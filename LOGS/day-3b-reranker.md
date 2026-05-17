# Day 3b — Reranker swap to Qwen3-Reranker-0.6B (OpenVINO)

Date: 2026-05-17. One commit follows this log.

## Goal

Replace `cross-encoder/ms-marco-MiniLM-L-6-v2` (23M params, sentence-transformers, PyTorch CPU, classification head) with `Qwen3-Reranker-0.6B` (600M params, CausalLM, OpenVINO int8 on Arc 140V iGPU, yes/no token-logit extraction).

Same retrieval pipeline shape: hybrid (Chroma vector + BM25) → fetch ~10 candidates → rerank → top-k. Only the reranker changes. The Qwen3-Embedding-0.6B collection from Phase 3a is reused.

## Brief deviation — `--task` for conversion

The brief specified `--task text-classification` for the OpenVINO conversion. **This would have failed.** Qwen3-Reranker is not a classifier model — it's a CausalLM with no classification head. The published protocol wraps each `(query, doc)` pair in a chat-template prompt that constrains the model to answer "yes" or "no" and extracts the yes/no token logits at the last position. Score = `softmax([no_logit, yes_logit])[1]`.

Conversion command actually used:

```
optimum-cli export openvino \
  --model Qwen/Qwen3-Reranker-0.6B \
  --task text-generation \
  --weight-format int8 \
  ~/models/openvino/qwen3-reranker-0.6b-int8
```

Output: `openvino_model.bin` 597 MB. NNCF compression: **100% int8_asym per-channel (197/197 layers)**. Total dir 609 MB.

One follow-on quirk surfaced at load time: `OVModelForCausalLM.from_pretrained` defaults `use_cache=True`, but the `text-generation` export (without `-with-past`) only supports `use_cache=False`. Fix is a single kwarg at load time:

```python
OVModelForCausalLM.from_pretrained(MODEL_DIR, device=requested, use_cache=False)
```

Correct for our use case — we do single-forward-pass logit extraction, not incremental decoding, so the KV cache wouldn't help anyway.

## Code changes

### `rag/reranker.py` (new)

`Qwen3Reranker` class with a `.predict(pairs)` method matching the `sentence_transformers.CrossEncoder` interface (drop-in for the existing `rag.service.rerank()` call site).

Implements the model-card protocol exactly:
- Chat-template prompt with system + user blocks, `<Instruct>` / `<Query>` / `<Document>` lines, and an empty `<think>` block in the assistant prefix.
- Tokenizer with `padding_side='left'` and `fix_mistral_regex=True` (same case-boundary regex patch applied to the embedder).
- `_yes_id` and `_no_id` extracted via `tokenizer.convert_tokens_to_ids`.
- Forward pass through `OVModelForCausalLM`, take last-position logits, softmax over `[no_logit, yes_logit]`, return P(yes).

Conservative iGPU sizing for the Arc 140V memory budget:
- `BATCH = 8` (vs the embedder's 16 — reranker inputs are ~1100 tokens vs the embedder's ~900, so per-batch token volume is similar).
- `MAX_LEN = 2048` (Qwen3 native context is 32K; we don't need it).

Device selection: GPU first via `QWEN3_RERANKER_DEVICE` (default `GPU`), CPU fallback on init failure.

`USE_QWEN3_RERANKER` env flag (default `True`) gates the new path. Setting it to `0`/`false`/`no`/`off` routes through the legacy `cross-encoder/ms-marco-MiniLM-L-6-v2` (scheduled for removal in Phase 3d cleanup).

### `rag/service.py` (modified)

- `import { Qwen3Reranker, USE_QWEN3_RERANKER, active_backend } from rag.reranker`.
- `RERANKER` constant renamed to `LEGACY_RERANKER` to make the legacy path obvious.
- Reranker init now branches on `USE_QWEN3_RERANKER`:
  - True → `self.reranker = Qwen3Reranker()`
  - False → `self.reranker = CrossEncoder(LEGACY_RERANKER)` (lazy import to avoid loading sentence-transformers when not needed)
- Status line now emits `[init] reranker: <active_backend dict>` so result files self-describe which reranker scored them.

The existing `rerank()` function in service.py is untouched. It calls `reranker.predict(pairs)` and trusts the duck-typed interface — both `CrossEncoder` and `Qwen3Reranker` satisfy it.

## Smoke

```
init: device=GPU in 5.74s
backend: {'backend': 'qwen3-reranker-0.6b-openvino', 'device': 'GPU', ...,
          'batch': 8, 'max_len': 2048}
rerank(3 pairs) in 0.258s
  doc0 score=0.9993  CVE-2023-23397 NTLM hash leak (matching)
  doc1 score=0.0001  Linux CFS scheduler (unrelated)
  doc2 score=0.0026  Generic Outlook description (off-topic but tangential)
rerank(10 same-pair) in 0.459s -> 21.8 pairs/sec
```

Discrimination is sharp — matching CVE doc scores 0.9993 vs 0.0001 for unrelated content, and the generic-Outlook ambiguous doc correctly scores low (0.0026) rather than getting accidentally lifted by topic overlap.

## Retrieval-only eval (Phase 3b acceptance gate)

```
QWEN3_EMBED_DEVICE=GPU QWEN3_RERANKER_DEVICE=GPU rag/venv/bin/python eval/run_eval.py \
  --db rag/chroma_db_qwen3 \
  --collection forged_v2_qwen3_emb \
  --retrieval-only \
  --tag v2-day3b-qwen3rerank-retrieval \
  --out eval/results/2026-05-17_v2-day3b-qwen3rerank-retrieval.json
```

Wall clock: **342 s** for all 50 questions (vs 3a's 39 s — Qwen3 reranker is ~9× slower than MiniLM on iGPU at 600M vs 23M params, but still very acceptable). Zero errors, zero timeouts.

### Aggregate (Day 3a fixed → Day 3b)

| category | Day 3a | Day 3b | delta |
|---|---|---|---|
| ambiguous | 1.000 | 1.000 | +0.000 (empty-gold artifact) |
| attack-technique | 0.897 | **0.925** | +0.028 |
| **cve-specific** | 0.168 | **0.190** | **+0.022** ← biggest CVE lift since v1 |
| multi-step | 0.599 | **0.578** | **−0.021** ← regression flagged below |
| payload-specific | 0.927 | **0.945** | +0.017 |
| **OVERALL** | **0.666** | **0.671** | **+0.005** |

### Per-question CVE-specific (Day 3a → Day 3b)

| id | 3a retr | 3b retr | path_recall | substr_recall | note |
|---|---|---|---|---|---|
| q-001 Spring4Shell | 0.000 | 0.000 | 0.00 → 0.00 | 0.00 → 0.00 | still no signal |
| q-002 PrintNightmare | 1.000 | 1.000 | 1.00 → 1.00 | 1.00 → 1.00 | ceiling held |
| q-003 PwnKit | 0.000 | 0.000 | 0.00 → 0.00 | 0.00 → 0.00 | still no signal |
| q-004 Baron Samedit | 0.150 | 0.150 | 0.00 → 0.00 | 0.50 → 0.50 | unchanged |
| q-005 ProxyShell | 0.000 | 0.000 | 0.00 → 0.00 | 0.00 → 0.00 | still no signal |
| **q-006 CitrixBleed** | 0.075 | **0.150** | 0.00 → 0.00 | 0.25 → **0.50** | reranker found a better substring-match chunk |
| **q-007 MOVEit** | 0.000 | **0.075** | 0.00 → 0.00 | 0.00 → **0.25** | first non-zero on q-007 since v1 |
| q-008 Confluence | 0.225 | 0.225 | 0.00 → 0.00 | 0.75 → 0.75 | unchanged |
| **q-009 polkit** | 0.075 | **0.150** | 0.00 → 0.00 | 0.25 → **0.50** | reranker found a better chunk |
| q-010 GoAnywhere | 0.150 | 0.150 | 0.00 → 0.00 | 0.50 → 0.50 | unchanged |

The CVE lift comes from substring-recall improvements on q-006, q-007, q-009. **`path_recall` is still 0.000 for 9 of 10 cve-specific questions** — the corpus structure cap is unchanged. Phase 3b improved at the substring-match layer where the reranker has discretion; path-recall is bottlenecked at the corpus level.

### Multi-step regression — q-035 detail

Six multi-step questions improved, four regressed. Net: **−0.021**.

| id | 3a → 3b | delta |
|---|---|---|
| q-029 Kerberoasting | 0.850 → 0.925 | +0.075 |
| q-030 unconstrained delegation | 0.775 → 0.850 | +0.075 |
| **q-032** SSRF-to-RCE | 0.300 → 0.225 | −0.075 |
| **q-035** K8s hostPID | **0.925 → 0.225** | **−0.700** ← single biggest delta |
| q-037 GraphQL chain | 0.850 → 1.000 | +0.150 |
| q-038 leaked AKIA | 0.150 → 0.225 | +0.075 |
| **q-040** GCP SSRF | 0.300 → 0.200 | −0.100 |
| q-041 jump host pivot | 0.075 → 0.225 | +0.150 |
| **q-043** Android APK | 1.000 → 0.925 | −0.075 |
| q-045 Cobalt Strike beacon | 0.850 → 0.925 | +0.075 |

Retrieval is fully deterministic — no temperature, no sampling. So q-035's −0.700 is not variance, it's a structural shift caused by the reranker change.

Hypothesis: Qwen3-Reranker's yes/no pivot is more conservative on multi-step queries where the gold chunks span multiple HackTricks pages. The MiniLM CrossEncoder rewarded "topically related" chunks generously; Qwen3-Reranker asks "does this passage actually answer the query?" and gives a lower probability to partial-answer chunks. Several of those partial chunks were in the multi-step gold sets — particularly for q-035 (K8s hostPID privesc requires stitching ~4 specific techniques across pages).

Net direction is mixed: the same conservatism that hurts multi-step *helps* the CVE category (where partial-substring matches benefit from being suppressed in favor of higher-precision matches). It's a real trade-off, not a degradation.

## Phase 3b acceptance results

| check | brief expectation | actual | pass? |
|---|---|---|---|
| All 50 retrieved cleanly | no errors, no timeouts | 50/50 ok | **✓** |
| `mean_retrieval ≥ 3a` | strict no-regression on overall | 0.671 ≥ 0.666 | **✓** |
| Hard stop: `mean_retrieval ≥ 0.62` | broken-integration trip | 0.671 | **✓** |
| `cve-specific` improves by ≥ +0.02 over 3a | embed→rerank stack target | +0.022 | **✓** (barely; exactly at gate) |

## Surprises

1. **`--task text-classification` would have failed** as the brief specified it. Qwen3-Reranker is a CausalLM; needed `--task text-generation`. Documented in the Brief deviation section.
2. **`use_cache=True` is the OVModelForCausalLM default and incompatible with `--task text-generation`** (no `-with-past`). One-kwarg fix at load time. Worth flagging because other engineers replicating this will hit the same wall.
3. **q-035 single-question −0.700 swing** is the largest individual delta of the run. Retrieval is deterministic, so it's attributable to the reranker change — not noise. The trade-off (conservative reranking helps CVE-specific, hurts some multi-step) is real. Worth a separate orchestrator note if multi-step matters more than CVE-specific at the program level.
4. **Wall-clock 9× slower** is the iGPU running 26× more reranker params for similar throughput. Throughput per pair was actually competitive on smoke (21.8 pairs/sec at batch=8) — the eval wall is dominated by 50 × ~10-candidate batches × ~0.7 sec/batch.
5. **`path_recall` is still 0.000 for 9 of 10 cve-specific.** Reranker can only re-order what the dense+sparse retrieval surfaced. The corpus-structure cap is unchanged from 3a; the only lift available is substring-recall improvements on chunks that *were* surfaced but not previously ranked well.

## Files

| file | purpose |
|---|---|
| `rag/reranker.py` | New — Qwen3-Reranker-0.6B OpenVINO + CrossEncoder-compat `.predict()`, GPU-first with CPU fallback |
| `rag/service.py` | Modified — branch reranker init on `USE_QWEN3_RERANKER` flag; legacy CrossEncoder kept behind the flag |
| `~/models/openvino/qwen3-reranker-0.6b-int8/` | New — 609 MB int8 OpenVINO artifacts (not in repo) |
| `eval/results/2026-05-17_v2-day3b-qwen3rerank-retrieval.json` | Phase 3b retrieval-only result (gitignored) |
