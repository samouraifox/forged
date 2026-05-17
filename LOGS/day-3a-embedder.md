# Day 3a — Embedder swap to Qwen3-Embedding-0.6B (OpenVINO)

Date: 2026-05-17. One commit follows this log.

## Goal

Replace `nomic-embed-text` (Ollama, 768-dim) with `Qwen3-Embedding-0.6B` (OpenVINO int8, 1024-dim) and re-embed the existing 14,308-chunk corpus into a new collection without disturbing v1. Generation layer, rubric, system prompt, and the questions file are LOCKED — the only variable changing in this phase is the embedding model.

## Setup

### OpenVINO install

```
rag/venv/bin/python -m pip install "openvino>=2025.0" "optimum[openvino]>=1.20"
```

Resolved: `openvino-2026.1.0`, `optimum-intel-1.27.0`, `nncf-3.1.0`, `onnx-1.21.0`. `transformers` was downgraded `5.8.1 → 4.57.6` (optimum-intel pins 4.x); `huggingface_hub` was downgraded `1.15.0 → 0.36.2`. No project code depends on `transformers>=5`, so the downgrade is harmless.

### Model conversion

```
optimum-cli export openvino \
  --model Qwen/Qwen3-Embedding-0.6B \
  --task feature-extraction \
  --weight-format int8 \
  ~/models/openvino/qwen3-embedding-0.6b-int8
```

Output (`~/models/openvino/qwen3-embedding-0.6b-int8/openvino_model.bin`): 616 MB. NNCF weight-compression summary: **99% int8_asym per-channel, 1% float** (3 of 198 layers stay FP16 — embedding + a norm or two). Total artifact dir: 627 MB including `openvino_tokenizer.*`, `openvino_detokenizer.*`, tokenizer JSON, and the chat template.

### GPU vs CPU

Tried `OVModelForFeatureExtraction.from_pretrained(..., device="GPU")` first and got:

```
[GPU] Can't get PERFORMANCE_HINT property as no supported devices found or
      an error happened during devices query.
[GPU] Please check OpenVINO documentation for GPU drivers setup guide.
```

Root cause: Intel Compute Runtime (`intel-compute-runtime` Arch package, provides `libze_intel_gpu.so` + Level Zero OpenCL on the Arc 140V iGPU) is **not installed at the OS level**. Only `intel-media-driver` (VAAPI, video decode) is present. `pacman -Qs intel-compute level-zero intel-opencl` returned nothing matching. The Lunar Lake `/dev/dri/{card0, renderD128}` device nodes exist, so the kernel-side GPU exposure is intact — the missing piece is the userland runtime.

**Decision: fall back to CPU for Phase 3a** per the brief's GPU-fallback-allowed clause. The embedder module's `_qwen3_lazy_init()` catches the GPU init exception and silently switches to `device="CPU"` on retry. Logged once per process; no impact on correctness.

To install the GPU runtime later (orchestrator decision; needs sudo):

```
sudo pacman -S intel-compute-runtime level-zero-loader
```

This would let the orchestrator re-run Phase 3a on GPU for a throughput comparison if interesting; correctness is unaffected.

## Code changes

### `rag/embedder.py` (new)

Single entry point `embed_texts(texts, *, is_query: bool) -> list[list[float]]` that handles both query and document encoding under Qwen3, with the legacy `nomic-embed-text` fallback gated by `USE_QWEN3_EMBEDDING` (default `True`).

Implements the model-card protocol exactly:
- Tokenizer with `padding_side='left'` (last-token pooling requires it).
- Queries are wrapped with `Instruct: <task>\nQuery: <text>` where `<task>` is a cybersecurity-specific instruction tight to the retrieval use case.
- Documents are encoded raw (no prefix).
- Pooling: last-token hidden state, left-padding-aware (matches the Qwen3 model-card function `last_token_pool`).
- Output: L2-normalized 1024-dim float vectors.

Device selection: tries `QWEN3_EMBED_DEVICE` (default `GPU`) first; falls back to `CPU` if iGPU init raises.

### `rag/service.py` (modified)

- Removed `import ollama` and `EMBED_MODEL = "nomic-embed-text"`.
- `embed(text)` now routes through `embedder.embed_texts([text], is_query=True)[0]`; the `@lru_cache(256)` wrapper is preserved for TUI repeat-query benefit (no help during eval since questions are unique).
- `RetrieveService.__init__(db_path, collection)` now takes a `collection` override (default still `"security"`). `initialize()` uses `self.collection_name` instead of the module-level `COLLECTION` constant.
- Init status line now prints `[init] embedder: <active_backend dict>` so the harness can confirm at startup which embedding backend the run is using.

### `rag/ingest.py` (modified)

- Replaced direct `ollama.embed` calls with `embedder.embed_texts(..., is_query=False)`.
- Added `--collection <name>` arg (default `"security"`). The `--reset` flag now scopes to the targeted collection only.
- Removed `MAX_CHARS_FOR_EMBED` and `EMBED_NUM_CTX` constants — Qwen3's tokenizer handles truncation at 8192 tokens which is well above the chunk cap.
- Print `[ingest] embedder: <active_backend dict>` at start.

### `rag/reembed.py` (new)

**Deviation from brief, surfaced explicitly to the orchestrator below.**

The brief asked for a fresh re-ingest from the source corpus via `rag/ingest.py`. The source corpus directory (`rag/corpus/{hacktricks,PayloadsAllTheThings,CheatSheetSeries,cti}`) is gitignored and was not preserved alongside `rag/chroma_db`. Only `.gitkeep` remains in `rag/corpus/`.

Re-downloading HackTricks, PayloadsAllTheThings, OWASP CheatSheets, and MITRE CTI would have added 30+ minutes AND introduced a confounding variable: those upstream sources are continuously updated, so the new corpus would differ from the one v1 was built against in ways unrelated to the embedder change.

The cleaner alternative — `rag/reembed.py` — reads `(chunk_id, document, metadata)` directly from the existing `rag/chroma_db/security` collection and writes a new collection with only the vector changed. Same chunk text byte-for-byte, same boundaries, same metadata. This is a *strictly cleaner* A/B than re-ingestion would have been.

Output: `rag/chroma_db_qwen3/forged_v2_qwen3_emb` with a fresh BM25 index. Both kept isolated from v1 so the existing `rag/chroma_db/security` collection remains untouched and reversible.

### `eval/run_eval.py` (modified)

- Added `--collection <name>` flag, default = the `COLLECTION` constant from `rag.service` (`"security"`). Plumbed through to `RetrieveService(collection=args.collection)`.
- Added `--retrieval-only` flag. When set, `stream_query` is skipped entirely; `score_retrieval` runs directly on `top_hits_raw`; `fact_score`, `hallucination_penalty`, and `hallucinations` are explicitly `None`/`[]`; `combined` collapses to `retrieval_score`. Order-of-magnitude faster than full inference.
- `rag_runtime.ensure_ollama_running` is now conditional on `not rag_embedder.USE_QWEN3_EMBEDDING` — Qwen3 needs no ollama, and the LLM has been on `llama-server` since Day 2. Same guard wraps the post-timeout `_kill_ollama_runner` recovery code.
- `config` block in the result JSON now records `collection`, `retrieval_only`, and the full `embedder.active_backend()` dict so result files self-describe their retrieval-stack identity.

### `.gitignore`

`rag/chroma_db/` → `rag/chroma_db/`, `rag/chroma_db_*/` (covers `chroma_db_qwen3`, future variants). Mirrored in `rag/.gitignore`.

## Smoke results

### `rag/embedder.py` standalone

```
init: device=CPU in 3.10s
backend: {'backend': 'qwen3-embedding-0.6b-openvino', 'device': 'CPU', ...,
          'dim': 1024, 'max_len': 8192}
q L2: 1.000000
d[0] L2: 1.000000
d[1] L2: 1.000000
cosine(CVE-23397 question, matching doc) = 0.5896
cosine(CVE-23397 question, unrelated CFS doc) = 0.2332
discrimination: +0.3563
```

L2 normalization works (norms exactly 1.0). The 1024-dim vectors discriminate sharply between the matching CVE doc and an unrelated Linux scheduler doc.

### `rag/reembed.py --limit 10`

Smoke ingest: 10 chunks → re-embedded + Chroma-written + BM25-rebuilt + completion message in 4.79s wall-clock (~3.1s of that is one-time model init). Round-trip wiring works.

## Re-embed run

Full re-embed: `rag/chroma_db/security` (14,308 chunks) → `rag/chroma_db_qwen3/forged_v2_qwen3_emb`.

Two attempts. The first crashed on a sharp GPU memory wall mid-corpus; the second succeeded after a config fix. See **Surprises** for the diagnostic detail.

| run | settings | result |
|---|---|---|
| Attempt 1 (CPU) | `device=CPU` (GPU runtime not installed yet) | Throughput 0.6 chunks/sec; killed at 3,328/14,308 after 1h 30m when it became clear we'd blow the 6-hour budget |
| GPU runtime install | `sudo pacman -S intel-compute-runtime level-zero-loader` (orchestrator step) | `intel-compute-runtime` provides `libze_intel_gpu.so.1`; `level-zero-loader` provides `libze_loader.so.1`. `openvino.Core().available_devices` now shows `['CPU', 'GPU']` with `GPU` resolving to `Intel(R) Arc(TM) Graphics (iGPU)`. |
| Attempt 2 (GPU, BATCH=64) | `device=GPU`, `BATCH=64`, `MAX_LEN=8192` | Got to 8,896/14,308 chunks (62%) at ~9 chunks/sec before session-kill stopped the process |
| Attempt 3 (GPU, BATCH=64, resume) | Same config, no `--reset` | Crashed on first batch with `CL_OUT_OF_RESOURCES` from the OpenCL driver — Arc 140V iGPU memory budget exceeded by `B × L²` activation pool at production-sized chunks. Once `CL_OUT_OF_RESOURCES` fires, OpenVINO warns subsequent calls may hang; the GPU plugin context went into a degraded state and every batch + per-chunk retry spun on the wedge. Process killed. |
| Attempt 4 (GPU, BATCH=16, resume) | `device=GPU`, `BATCH=16`, `MAX_LEN=2048` | **Completed.** 5,412 chunks re-embedded in 8 min wall-clock (avg 1.42 s/batch, ~11 docs/sec under real chunk-length conditions). Python RSS held at 1.9 GB the whole time (vs 18 GB on CPU). BM25 index rebuilt over the full 14,308 chunks in ~3 sec via bm25s. |

Final state of `rag/chroma_db_qwen3/forged_v2_qwen3_emb`:
- **14,308 chunks** — identical id-set + text + metadata to the source `security` collection; only the vector dimension/values changed (768 nomic → 1024 Qwen3).
- BM25 snapshot: `rag/chroma_db_qwen3/bm25s_index/` + `bm25_meta.pkl` (19 MB).
- Total dir: 218 MB (vs 144 MB for v1's `chroma_db/`; the 33% larger footprint reflects the 1024-dim vectors).
- Dropped chunks: 0.

## Retrieval-only eval (Phase 3a acceptance gate)

```
QWEN3_EMBED_DEVICE=GPU rag/venv/bin/python eval/run_eval.py \
  --db rag/chroma_db_qwen3 \
  --collection forged_v2_qwen3_emb \
  --retrieval-only \
  --tag v2-day3a-qwen3emb-retrieval \
  --out eval/results/2026-05-17_v2-day3a-qwen3emb-retrieval.json
```

Wall clock: **39.3 seconds** for all 50 questions (no timeouts, no errors). Per-question latency was 0.6-0.8 s — that's hybrid retrieve + rerank + scoring; the embedder itself was a tiny fraction of that.

| category | v1 retrieval | Day 2 retrieval | **Day 3a retrieval** | delta vs Day 2 |
|---|---|---|---|---|
| ambiguous | 1.000 | 1.000 | **1.000** | +0.000 (artifact — empty gold) |
| attack-technique | 0.809 | 0.809 | **0.897** | **+0.088** ← biggest win |
| cve-specific | 0.160 | 0.160 | **0.168** | **+0.008** ← marginal |
| multi-step | 0.603 | 0.603 | **0.599** | -0.004 (noise) |
| payload-specific | 0.927 | 0.927 | **0.927** | +0.000 (ceiling) |
| **OVERALL** | **0.652** | **0.652** | **0.666** | **+0.014** |

(Day 2's retrieval scores were identical to v1's by construction — Day 2 only changed the LLM, not the retrieval stack.)

### Per-question CVE-specific breakdown

| id | retrieval | path_recall | substring_recall | question |
|---|---|---|---|---|
| q-001 | 0.000 | 0.000 | 0.000 | Spring4Shell CVE-2022-22965 |
| q-002 | **1.000** | **1.000** | 1.000 | PrintNightmare CVE-2021-34527 |
| q-003 | 0.000 | 0.000 | 0.000 | PwnKit CVE-2021-4034 |
| q-004 | 0.150 | 0.000 | 0.500 | Baron Samedit CVE-2021-3156 |
| q-005 | 0.000 | 0.000 | 0.000 | ProxyShell |
| q-006 | 0.075 | 0.000 | 0.250 | CitrixBleed CVE-2023-4966 |
| q-007 | 0.000 | 0.000 | 0.000 | MOVEit CVE-2023-34362 |
| q-008 | 0.225 | 0.000 | 0.750 | Confluence CVE-2022-26134 vs CVE-2023-22515 |
| q-009 | 0.075 | 0.000 | 0.250 | polkit CVE-2021-3560 |
| q-010 | 0.150 | 0.000 | 0.500 | GoAnywhere MFT CVE-2023-0669 |

**`path_recall == 0.000` for 9 of 10 cve-specific questions.** The gold-label `rel_path` strings (CVE IDs as path fragments) don't match how the corpus is organized — HackTricks pages are titled by attack technique or platform, not by CVE. The Qwen3 embedder is doing slightly better at semantic substring matching (5 of 10 now have non-zero substring recall, vs the v1 number), but the *path-recall ceiling is fixed by corpus structure*, not by embedding quality.

## Phase 3a acceptance results

| check | brief expectation | actual | pass? |
|---|---|---|---|
| All 50 questions retrieved without errors | non-degenerate vectors, no NaNs, no timeouts | 50/50 ok, 0 timeouts | **✓** |
| mean_retrieval_score ≥ 0.65 | strict regression guard | 0.666 | **✓** (barely; +0.014 vs baseline) |
| Hard stop: mean_retrieval ≥ 0.62 | broken-integration trip | 0.666 | **✓** |
| cve-specific retrieval > 0.16 strict | moves the primary target | 0.168 | **✓** |
| Realistic cve-specific ≥ 0.20 | embedder swap target | 0.168 | **✗** (-0.032 below) |

Phase 3a passes hard stops and strict-improvement gates. **Realistic-target on cve-specific is not met by the embedder alone.** Continuing to 3b and 3c per the brief's structure; the final pass-or-stop decision rides on the post-3c number.

## Post-commit follow-up: `fix_mistral_regex=True`

The tokenizer was emitting a load-time warning pointing at HF discussion #84 on `mistralai/Mistral-Small-3.1-24B-Instruct-2503` — the pre_tokenizer regex in `tokenizer.json` is missing the case-boundary alternation that Mistral and Qwen3 are supposed to use. The flag `fix_mistral_regex=True` on `AutoTokenizer.from_pretrained` patches the regex at load time.

Inspected the actual `tokenizer.json` in `~/models/openvino/qwen3-embedding-0.6b-int8/tokenizer.json`: pre_tokenizer regex matches the "incorrect" Mistral pattern. Confirmed.

Compared tokenization on 10 cybersec strings:

| string | broken | fixed | differs? |
|---|---|---|---|
| PrintNightmare CVE-2021-34527 | 15 tokens | 15 tokens | no |
| ProxyShell | 2 tokens | 2 tokens | no |
| Spring4Shell CVE-2022-22965 | 15 tokens | 15 tokens | no |
| CitrixBleed (CVE-2023-4966) | 18 tokens | 18 tokens | **yes** |
| NTLM hash leak via PidLidReminderFileParameter | 12 | 12 | no |
| PwnKit pkexec heap overflow | 7 | 7 | no |
| MOVEit Transfer SQLi-to-RCE | 8 | 8 | no |
| polkit DBus authentication bypass | 6 | 6 | no |
| # Linux Privilege Escalation > LD_PRELOAD | 11 | 11 | no |
| Baron Samedit (CVE-2021-3156) — sudoedit heap overflow | 22 | 22 | no |

Only 1/10. For CitrixBleed: broken tokenizes "Citrix" as `['Cit', 'ri', 'xB', 'le', 'ed']` (the `x` merges with `B` of `Bleed`, crossing the case boundary), fixed gives `['Cit', 'rix', 'B', 'le', 'ed']` (clean case-boundary split). 2 token IDs differ out of 18 (~11% for that one string).

Applied the fix in `rag/embedder.py::_qwen3_lazy_init()`. The OpenVINO model takes input_ids only, so no model re-export was needed — only the HF AutoTokenizer load changed. Re-embedded the entire corpus with `--reset`.

**Result vs broken-regex run (per-question diff, identical scoring rubric):**

| measurement | result |
|---|---|
| Questions with changed `retrieval_score` | **0 / 50** |
| Questions with any chunk-swap in top-5 | 4 / 50 (q-007 MOVEit, q-042 Evilginx2, q-047 + q-050 ambiguous) |
| All aggregate + per-category numbers | byte-identical to the broken run |

The fix DID change the candidate set on a handful of questions, but the swapped chunks weren't in the gold-recall set, so the deterministic rubric didn't notice. **At our eval granularity, broken and fixed regex are indistinguishable.** Keeping the fix anyway — the model was *trained* against the corrected tokenization, and Phase 3c will re-embed under contextual retrieval, so having the embedder authoritative is the right state.

Canonical Phase 3a retrieval result: `eval/results/2026-05-17_v2-day3a-qwen3emb-fixed-retrieval.json`. The earlier `..._qwen3emb-retrieval.json` is superseded (kept locally for diff audits; both are gitignored).

## Surprises

1. **The brief's `--task text-classification` would have failed for the reranker** (separate phase, but worth noting now): Qwen3-Reranker-0.6B is a CausalLM that emits yes/no token logits, not a classifier head. I'll surface the exact deviation in `day-3b-reranker.md`.

2. **Intel Arc 140V iGPU memory blew up at production batch sizes despite a clean smoke.** The first GPU smoke used ~50-token test strings and passed cleanly at BATCH=64 (158 docs/sec). Real chunks reach 900 tokens; attention activation memory is `O(B × L²)` per layer, so the production workload demanded ~18× more activation memory than the smoke had measured. The OpenCL driver hit `CL_OUT_OF_RESOURCES` on the first real batch and went into a wedged state where every subsequent retry also failed (OpenVINO explicitly warns "subsequent OpenCL API calls may hang" after this error). Fix was BATCH=64 → 16 + MAX_LEN=8192 → 2048. The smaller batch knocks per-batch memory to ~1/4; the tighter MAX_LEN caps any pathological long chunk's quadratic blow-up. Comments added in code so this isn't "optimized" back later.

3. **CPU run was 25× slower than projected.** Pre-flight projection said 5-15 min for the full re-embed; observed CPU throughput at production sizes was ~0.6 docs/sec, with per-batch time *growing* from 60s to 200s as the run progressed (OpenVINO was caching compiled variants for each new input shape; RSS hit 18 GB before I stopped it at 23% completion). GPU at BATCH=16 holds steady ~11 docs/sec with 1.9 GB RSS — the right runtime by every measurable axis.

4. **Path-recall is structurally capped on cve-specific.** 9 of 10 cve-specific questions have path_recall = 0.0 not because retrieval is failing semantically, but because the corpus organizes pages by attack technique / platform, not by CVE ID. The embedder swap cannot fix this; only corpus restructuring (or richer chunk-level metadata that surfaces CVE identifiers) can. This is the bottleneck the brief warned about in its end-of-3c stop condition.

5. **attack-technique retrieval jumped +0.088 (0.809 → 0.897) from the embedder swap alone.** The Qwen3 embedder's task-aware Instruct prefix likely helps it match T-code-style queries against the MITRE CTI corpus where the technique IDs live in chunk content. Unexpected and welcome.

## Files

| file | purpose |
|---|---|
| `rag/embedder.py` | New — Qwen3-Embedding-0.6B via OpenVINO + ollama fallback, GPU-first with CPU fallback |
| `rag/reembed.py` | New — re-embed an existing collection into a new one (substitutes for `ingest.py` since the source corpus dir is empty) |
| `rag/service.py` | Modified — embedder routing, collection override, init status |
| `rag/ingest.py` | Modified — embedder routing, `--collection` flag |
| `eval/run_eval.py` | Modified — `--collection`, `--retrieval-only`, conditional ollama startup |
| `rag/chroma_db_qwen3/forged_v2_qwen3_emb` | New collection, 14,308 chunks, 1024-dim Qwen3 vectors, fresh BM25 (gitignored) |
| `eval/results/2026-05-17_v2-day3a-qwen3emb-retrieval.json` | Phase 3a retrieval-only result (gitignored) |

## Files

| file | purpose |
|---|---|
| `rag/embedder.py` | New — Qwen3-Embedding-0.6B via OpenVINO + ollama fallback |
| `rag/reembed.py` | New — copy + re-embed existing collection into a new collection (replaces brief's ingest path because the source corpus is gone) |
| `rag/service.py` | Modified — embedder routing, collection override, init status |
| `rag/ingest.py` | Modified — embedder routing, `--collection` flag |
| `eval/run_eval.py` | Modified — `--collection`, `--retrieval-only`, conditional ollama startup |
| `rag/chroma_db_qwen3/forged_v2_qwen3_emb` | New collection, 14,308 chunks, 1024-dim Qwen3 vectors, fresh BM25 |
| `eval/results/2026-05-17_v2-day3a-qwen3emb-retrieval.json` | Phase 3a retrieval-only result |
