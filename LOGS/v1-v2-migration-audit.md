# v1 → v2 Migration Audit — Stale-default cleanup

**Date:** 2026-05-20
**Trigger:** Interactive TUI run hit "Collection does not exist" after a `rag/tui_worker.py` band-aid that updated v2 defaults but left the launcher chain still pointing at the v1 DB path.
**Outcome:** Root cause was `localchat_tui/backend.py` passing `--db rag/chroma_db` (v1 path) into a worker whose `--collection` default had been updated to v2 → mismatch. Cleaned by routing all entry-point defaults through a new single source of truth `rag/config.py`.

---

## 1. Actual v2 collection name (Step 1 ground truth)

Enumerated every `rag/chroma_db*` directory with the venv chromadb client:

| DB path                              | Collection                                    | Chunks | Phase                                |
|--------------------------------------|-----------------------------------------------|--------|--------------------------------------|
| `rag/chroma_db`                      | `security`                                    | 14,308 | v1 archive (DeepSeek + nomic)        |
| `rag/chroma_db_qwen3`                | `forged_v2_qwen3_emb`                         | 14,308 | v2 first cut (raw Qwen3 embed)       |
| `rag/chroma_db_qwen3_partial_ctx`    | `forged_v2_qwen3_emb_context_partial_1421`    | 14,308 | v2 contextualized partial            |
| `rag/chroma_db_cve_arm_a`            | `forged_v2_qwen3_emb_cve_combined`            | 14,341 | ablation arm A                       |
| `rag/chroma_db_cve_arm_b`            | `forged_v2_qwen3_emb_cve_combined`            | 14,341 | ablation arm B                       |
| **`rag/chroma_db_cve_full`**         | **`forged_v2_qwen3_emb_cve_full`**            | **14,425** | **Phase 3.5+2 PRODUCTION**       |

Production is `rag/chroma_db_cve_full / forged_v2_qwen3_emb_cve_full` (14,425 chunks). The band-aid's collection-name assumption was correct; the bug was elsewhere.

## 2. v1 references — verdict table

Active code only. Archive/replay artifacts (LOGS/, eval/review-bundles/, frozen result JSONs) excluded.

| File:line | Reference | Verdict |
|---|---|---|
| `rag/service.py:20-21` | `LLM_MODEL = "hermes-4-14b"` / `LLM_DISPLAY_NAME = "Hermes-4-14B (Q6_K, llama-server)"` | **v2-correct → reroute via config** (consolidate) |
| `rag/service.py:22` | `LLM_BASE_URL = "http://127.0.0.1:8080/v1"` | **v2-correct → reroute via config** |
| `rag/service.py:25` | `LEGACY_RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"` | v1-correct-fallback (used when `USE_QWEN3_RERANKER=0`) — kept |
| `rag/service.py:26-27` | `DEFAULT_DB = ".../chroma_db"`, `COLLECTION = "security"` | **v1-stale → fixed via config** |
| `rag/tui_worker.py:65-66` | inline `"chroma_db_cve_full"` / `"forged_v2_qwen3_emb_cve_full"` band-aid defaults | **v2-correct but inline string literals → fixed via config** |
| `localchat_tui/backend.py:64` | `self.worker_db = root / "rag" / "chroma_db"` | **v1-stale (ROOT CAUSE) → fixed via config** |
| `localchat_tui/backend.py:68` | `model="DeepSeek-R1 abliterated (starting…)"` | **v1-stale → fixed via config** |
| `localchat_tui/state.py:67` | `model: str = "DeepSeek-R1 abliterated"` | **v1-stale → fixed inline** (transient startup placeholder, overwritten by descriptor) |
| `rag/embedder.py:144-181` | Legacy `nomic-embed-text` fallback path | v1-correct-fallback (gated on `USE_QWEN3_EMBEDDING=0`) — kept |
| `rag/reranker.py:3,168` | Comments referencing `ms-marco-MiniLM` lineage | v1-correct-docstring — kept |
| `rag/ingest.py:25-26,109` | `DEFAULT_DB="chroma_db"`, `DEFAULT_COLLECTION="security"` | v1-stale **but** orchestrator brief says "Eval harness, smoke scripts, ingest scripts can override via args... Don't change those" → **left untouched** |
| `eval/run_eval.py:104` | `default=REPO_ROOT / "rag" / "chroma_db"` | v1-stale, ingest-rule scope — **left untouched** |
| `eval/run_eval.py:68,140` | `from rag.service import COLLECTION as DEFAULT_COLLECTION` | cascades to v2 via service.py constant change — see §5 below |
| `eval/rescore.py:69,72` | `default=REPO_ROOT / "rag" / "chroma_db"`, `default="security"` | v1-stale, ingest-rule scope — **left untouched** |
| `eval/review-bundles/_enrich_deep_dive.py:39,45` | Explicit paths to `chroma_db_qwen3` and `chroma_db_qwen3_partial_ctx` | archive replay (intentional, specific phases) — kept |
| `rag/build_cve_ablation.py:44-48` | Explicit `BASELINE_DB`, `ARM_A_DB`, `ARM_B_DB` | phase-specific ingestion (intentional) — kept |
| `rag/build_cve_ingest.py:48-51` | Explicit `BASELINE_DB`, `DST_DB` paths | phase-specific ingestion (intentional) — kept |
| `rag/contextualize/_prep_work_items.py:15` | Explicit `path="rag/chroma_db_qwen3"` | phase-specific tool — kept |
| `rag/reembed.py:6` | Docstring references `chroma_db` | doc-only — kept |
| `LOGS/linkedin-charts/generate_charts.py:*` | Chart labels documenting v1↔v2 contrast | archive artifact — kept |

## 3. RetrieveService instantiation sites

```
eval/run_eval.py:503    RetrieveService(db_path=str(args.db), collection=args.collection)
rag/tui_worker.py:67    RetrieveService(db_path=db_path, collection=collection)
rag/preflight_3d.py:85  RetrieveService(db_path=str(DB), collection=COL)
rag/smoke_cve_ingest.py:84  RetrieveService(db_path=str(DST_DB), collection=DST_COLLECTION)
rag/smoke_rerank_diff.py:48 RetrieveService(db_path=str(DB), collection=COL)
```

All five pass explicit `db_path` and `collection` — none rely on `RetrieveService.__init__` defaults. So the service-level default change is purely defensive (catches future callers + the localchat TUI which previously passed v1 path through the `--db` arg).

## 4. Files modified

1. `rag/config.py` (NEW) — single source of truth: `V2_DB_PATH`, `V2_COLLECTION`, `V2_EMBEDDER_MODEL`, `V2_RERANKER_MODEL`, `V2_LLM_BACKEND`, `V2_LLM_MODEL`, `V2_LLM_DISPLAY_NAME`, `V2_LLM_BASE_URL`.
2. `rag/service.py` — `LLM_MODEL`, `LLM_DISPLAY_NAME`, `LLM_BASE_URL`, `DEFAULT_DB`, `COLLECTION` now reference `rag.config`.
3. `rag/tui_worker.py` — `--db`/`--collection` fallback now `V2_DB_PATH`/`V2_COLLECTION` from config; dropped unused `pathlib.Path` import.
4. `localchat_tui/backend.py` — `self.worker_db = Path(V2_DB_PATH)`; descriptor model = `f"{V2_LLM_DISPLAY_NAME} (starting…)"`. Lazy import of `rag.config` inside `__init__` to keep module-load decoupled.
5. `localchat_tui/state.py` — `ModeState.model` default updated to `"Hermes-4-14B (Q6_K, llama-server)"` (inline string; this is a transient startup placeholder, immediately overwritten by descriptor when the worker emits its `ready` event).

## 5. Cascade through service.py constants

`eval/run_eval.py:68` imports `COLLECTION as DEFAULT_COLLECTION` from `rag.service`. The audit changes `service.COLLECTION` from `"security"` (v1) to `V2_COLLECTION` (v2). Effect: `eval/run_eval.py`'s argparse default for `--collection` cascades to v2.

The audit does NOT modify `eval/run_eval.py` itself (per the orchestrator's brief: "Eval harness, smoke scripts, ingest scripts can override via args as today (that's correct behavior). Don't change those — just fix the implicit defaults.").

Practical impact: the eval harness is always invoked with explicit `--db` and `--collection` args in every smoke/eval run on file (Day 3a–3d, Phase 3.5+2). The default cascade only changes behavior for the never-used "no-args" path. No archived result reproduction is affected — archive replay reads the recorded config from the result JSON, not from argparse defaults.

There is a residual internal inconsistency in `eval/run_eval.py:104`: the hardcoded v1 `--db` default still points at `rag/chroma_db`, while the imported `--collection` default cascades to v2. Running eval with no args would attempt the v2 collection on the v1 DB → same kind of mismatch the TUI hit. Left as-is per the "don't touch eval/rescore/ingest" instruction; flagged here for the orchestrator's review.

## 6. Verification

### 6.1 Compile + import wiring

```
$ rag/venv/bin/python -c "
from rag.config import V2_DB_PATH, V2_COLLECTION, V2_LLM_DISPLAY_NAME
from rag.service import DEFAULT_DB, COLLECTION, LLM_DISPLAY_NAME
assert DEFAULT_DB == V2_DB_PATH
assert COLLECTION == V2_COLLECTION
assert LLM_DISPLAY_NAME == V2_LLM_DISPLAY_NAME
"
OK

$ rag/venv/bin/python -m py_compile rag/tui_worker.py rag/service.py rag/config.py \
    localchat_tui/backend.py localchat_tui/state.py
OK
```

### 6.2 Worker subprocess end-to-end (no llama-server required)

Launched `python -m rag.tui_worker` with no args, read events from stdout:

```
status: checking ollama runtime
status: ollama already running; verifying listener and API
status: ollama runtime ready
status: [init] opening vector store at .../rag/chroma_db_cve_full (collection=forged_v2_qwen3_emb_cve_full)
status: [init] loading BM25 index
status: [init] loading reranker: Qwen3-Reranker-0.6B (OpenVINO)
status: [init] embedder: {backend: qwen3-embedding-0.6b-openvino, dim: 1024, max_len: 2048}
status: [init] reranker: {backend: qwen3-reranker-0.6b-openvino, batch: 4, max_len: 1024}
status: [init] generation backend: Hermes-4-14B (Q6_K, llama-server) @ http://127.0.0.1:8080/v1
status: [init] backend ready over 14425 chunks
ready: {provider: local, backend: hacker_lm, model: 'Hermes-4-14B (Q6_K, llama-server)', think_control: prompt-policy}
```

- ✅ No "Collection does not exist" error
- ✅ No dimension mismatch
- ✅ Correct collection name `forged_v2_qwen3_emb_cve_full`, 14,425 chunks (matches §1 ground truth)
- ✅ Embedder is Qwen3 1024-dim (matches collection dim)
- ✅ Ready event emits `model: Hermes-4-14B (Q6_K, llama-server)` → flows into TUI status bar descriptor

Then sent a RAG `request` (topk=3, source=None, RAG on, think off, no LLM call required because we read the `retrieved_context` event):

```
status: [retrieve] hybrid search over 14425 chunks…
status: [retrieve] 16 candidates in 3368 ms -> reranking
retrieved_context: 652 chars (3 reranked chunks)
```

- ✅ Hybrid search returns 16 dense+sparse candidates
- ✅ Reranker reduces to top-3
- ✅ Retrieved-context event delivers chunks to the TUI

### 6.3 Status bar — analysis

Bottom status bar in the TUI is populated from `descriptor.model` (set in `backend.py._ensure_process` when the worker emits `ready`). Before the fix:

1. Worker started, opened `rag/chroma_db` (v1)
2. Tried `client.get_collection("forged_v2_qwen3_emb_cve_full")` — fails with "Collection does not exist"
3. `startup()` raised → emitted `{type: error, fatal: true}`
4. `backend.py:188` raised `RuntimeError` → TUI showed the error in the chat pane
5. **No `ready` event was ever received** → descriptor still held the initial placeholder → status bar widget rendered with empty/initial state

After the fix:

1. Worker opens `rag/chroma_db_cve_full` (v2)
2. Collection exists, 14,425 chunks
3. `startup()` completes → emits `ready` with model name
4. `backend.py` updates descriptor → status bar renders model + uptime + mode states

The status bar regression and the "Collection does not exist" error were the same root cause: the worker crashed before `ready`. Fixing the path fixes both.

### 6.4 TUI end-to-end (manual orchestrator verification)

llama-server (Hermes-4-14B Q6_K, ~24 GB RAM) is not running at audit time. Launching it for a full TUI smoke is a heavy resource operation that I'm not taking autonomously. The worker-level verification above covers the audit's stated failure mode (Collection error + status bar empty). End-to-end Hermes streaming through the TUI uses unchanged code in the LLM path and was working in the Day 3d / Phase 3.5+2 runs that ship under the same `RetrieveService.stream_query` code path.

Recommended manual smoke for the orchestrator:

```
scripts/llama-server.sh   # or direct llama-server invocation with Q4 KV per brief
./hacker_lm               # confirm status bar renders + ask a CVE question
```

## 7. Out-of-scope findings (not changed)

- `hacker_lm:36` and `rag/tui_worker.py:31` unconditionally invoke `ensure_ollama_running`. With the v2 default stack (Qwen3 OpenVINO + Hermes llama-server), ollama is unused. The gate fires regardless of `USE_QWEN3_EMBEDDING` and would fail the TUI startup on a v2-only host that hasn't installed ollama. Surfaced for orchestrator review.
- `eval/run_eval.py:104` hardcodes the v1 `--db` default while the `--collection` default now cascades to v2 via service.COLLECTION — internal inconsistency. Left per "don't change ingest/eval scripts" rule. Surfaced for orchestrator review.
- `scripts/llama-server.sh` still has `--cache-type-k q8_0 --cache-type-v q8_0` (Q8) while the Day 8-9 brief specified Q4 KV. Pre-existing finding (also noted in `project_forged_day8_9_adaptive_rag.md`); not touched here.

## 8. What did NOT need changing

- All explicit `RetrieveService(db_path=..., collection=...)` call sites (eval/run_eval, smoke scripts) — they were already passing v2 args.
- All `rag.config.V2_*` consumers are now type-stable single-line imports — no fallback path, no try/except, no "v1 then v2" shim.
- `rag/embedder.py` and `rag/reranker.py` legacy v1 paths — gated on env vars (`USE_QWEN3_EMBEDDING=0`, `USE_QWEN3_RERANKER=0`), behave as opt-in archive-mode rather than implicit defaults. No "auto-fallback to v1" anywhere.

---

**Status:** Committed locally. Not pushed.
