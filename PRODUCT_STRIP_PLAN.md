# PRODUCT_STRIP_PLAN

Status: Phase 1 only. No cleanup has been executed yet.

Goal: reduce this copied repo to the real `hacker_lm` product path while preserving the current runnable product and keeping only the files needed to run it, maintain it, and evolve it safely.

Decision rule used here:
- Keep anything that is on the proven startup/runtime path.
- Keep off-path tooling only when it is needed to maintain the live product.
- Quarantine historical or secondary systems before deleting them.
- If evidence is incomplete, keep the item and mark it uncertain.

## 1. Proven Main Product Path

The current active execution path is:

1. User runs `./hacker_lm`.
   - Evidence: `hacker_lm:12-49`
   - The launcher requires `python3`, hard-requires `rag/venv/bin/python`, runs `rag.runtime --ensure-ollama`, then launches `python3 -m localchat_tui` or `uv run --with textual python -m localchat_tui`.

2. `python3 -m localchat_tui` enters the Textual app.
   - Evidence: `localchat_tui/__main__.py:1-3`, `localchat_tui/main.py:3-8`
   - `LocalChatApp(adapter=HackerLMBackendAdapter()).run()` is the real frontend entrypoint.

3. The TUI boots the real backend worker, not a mock backend.
   - Evidence: `localchat_tui/app.py:43-45,67-72,128-143`
   - On mount, the app calls `bootstrap_backend()`, which calls `adapter.startup()`.

4. The backend adapter points at `rag/venv` and `rag/chroma_db`, then spawns `rag.tui_worker`.
   - Evidence: `localchat_tui/backend.py:61-66,146-169`
   - The real adapter uses `rag/venv/bin/python` and `rag/chroma_db`, then starts `-m rag.tui_worker --db rag/chroma_db`.

5. The worker ensures Ollama and delegates all real query work to `RetrieveService`.
   - Evidence: `rag/tui_worker.py:28-39,42-65,67-89`
   - Startup calls `ensure_ollama_running()` and initializes `RetrieveService`.

6. `RetrieveService` is the retrieval + generation truth.
   - Evidence: `rag/service.py:18-27,114-120,302-343,345-430,432-520`
   - It loads Chroma, loads `bm25s_index` plus `bm25_meta.pkl`, loads the reranker, builds prompts, and calls `ollama.generate(model='hacker-guide', ...)`.

7. The live runtime depends on the checked-in model alias definition and the checked-in local index.
   - Evidence: `Modelfile:1-35`, `rag/service.py:20-23,332-339`, `localchat_tui/backend.py:64-65`
   - The current intended alias is `hacker-guide`; the live runtime reads from `rag/chroma_db`.

## 2. Keep

These items are on the main product path or are needed to maintain it.

| Path | Why keep | Evidence |
| --- | --- | --- |
| `hacker_lm` | Canonical launcher. | `hacker_lm:12-49` |
| `localchat_tui/` | Active frontend, state, styling, widgets. | `localchat_tui/main.py:3-8`, `localchat_tui/app.py:30-261`, `localchat_tui/styles.tcss:1-260` |
| `rag/runtime.py` | Active Ollama startup/check path. | `hacker_lm:37`, `rag/tui_worker.py:28-30`, `rag/runtime.py:25-58` |
| `rag/tui_worker.py` | Real backend worker transport. | `localchat_tui/backend.py:157-169`, `rag/tui_worker.py:62-89` |
| `rag/service.py` | Real retrieval, reranking, prompt assembly, generation. | `rag/service.py:302-520` |
| `rag/__init__.py` | Package marker for `python -m rag.*`. | `rag/__init__.py:1` |
| `rag/chroma_db/` except `bm25_corpus.pkl` | Required local vector + sparse index. | `localchat_tui/backend.py:65`, `rag/service.py:117-120,332-339` |
| `Modelfile` | Source of truth for rebuilding `hacker-guide`. | `README.md:29-33`, `Modelfile:1-35` |
| `requirements-tui.txt` | Minimal frontend dependency file. | `hacker_lm:39-48`, `requirements-tui.txt:1` |
| `rag/requirements.txt` | Backend dependency manifest, though it should be trimmed later. | `rag/service.py:14-17`, `rag/ingest.py:7-9,151`, `rag/requirements.txt:1-7` |
| `rag/ingest.py`, `rag/chunker.py`, `rag/mitre_loader.py`, `rag/corpus/` | Not startup-path, but needed to refresh or evolve the live local index. | `rag/ingest.py:27-32,83-170`, `rag/chunker.py:69-97`, `rag/mitre_loader.py:5-56` |
| `rag/venv/` | Hard-required by the current launcher and backend adapter. | `hacker_lm:9,32-38`, `localchat_tui/backend.py:64,159-165` |
| `README.md` | Should remain as the primary run/development doc, but must be rewritten to match the stripped repo. | `README.md:1-90` |

## 3. Quarantine Candidates

These items are outside the main product path and should move to `_removed_from_product/` in Phase 2 unless a last-minute contradiction appears.

| Path | Proposed action | Concrete evidence | Risk |
| --- | --- | --- | --- |
| `bench/` | Quarantine whole directory. | No active startup/runtime file references it: `hacker_lm:12-49`, `localchat_tui/main.py:3-8`, `localchat_tui/backend.py:61-169`, `rag/tui_worker.py:62-89`, `rag/service.py:302-520`. It is also stale: `bench/run_single.py:33-38` expects `retrieve.PROMPT_TEMPLATE`, `generate`, and `setup`, but current `rag/retrieve.py:1-206` exposes a REPL wrapper around `RetrieveService` instead. `bench/config.py:323-358` rewrites `Modelfile`, recreates `hacker-guide`, and restarts Ollama, which is benchmark-specific mutation, not product runtime. | Low runtime risk. Historical benchmark data/workflows become archived instead of live. |
| `rag/retrieve.py` | Quarantine as legacy secondary interface. | The real app path never imports it: `localchat_tui/main.py:3-8`, `localchat_tui/backend.py:61-169`, `rag/tui_worker.py:42-89`. Current references come from old docs/help and bench only: `README.md:53-57`, `hacker_lm:21-22`, `bench/run_single.py:27`. | Medium. Removes a secondary CLI smoke path. |
| `rag/cli_ui.py` | Quarantine with `rag/retrieve.py`. | Only the legacy REPL imports it: `rag/retrieve.py:7-12,140-185`. Nothing on the TUI path uses it. | Medium only because it removes the legacy REPL UI along with `rag/retrieve.py`. |
| `CONTEXT_FOR_GPT.md` | Quarantine after extracting any needed truths into `PRODUCT_STRUCTURE.md`. | Not part of startup/import/runtime. It explicitly documents stale or non-primary areas like bench, `MockBackendAdapter`, `Modelfile.bak`, and `.claude/settings.local.json`: `CONTEXT_FOR_GPT.md:45-56,92-105`. | Low. Useful history moves out of the active repo surface. |
| `upgrade-paths.txt` | Quarantine. | Not referenced by runtime/imports. It is a planning note, not an operational doc: `upgrade-paths.txt:1-82`. | Low. |
| `.claude/settings.local.json` | Quarantine. | Not part of product runtime/imports. It contains stale absolute paths and `mr_robot`-era permissions: `.claude/settings.local.json:4-38`. | Low. Tool-local config only. |
| `Modelfile.bak` | Quarantine with benchmark leftovers. | Active product uses `Modelfile`, not `.bak`: `README.md:29-33`, `Modelfile:1-35`. The only concrete code reference is benchmark code: `bench/config.py:31-32,327-358`. | Low. |
| `rag/chroma_db/bm25_corpus.pkl` | Quarantine. | The active service loads only `bm25s_index` and `bm25_meta.pkl`: `rag/service.py:114-120`. No active runtime file reads `bm25_corpus.pkl`. | Low. |

## 4. Safe Delete Candidates

These look like safe junk rather than historical subsystems.

| Path | Proposed action | Concrete evidence |
| --- | --- | --- |
| `.codex` | Delete. | File is empty and has no runtime references. Audit result: empty file. |
| Repo-level `__pycache__/` directories outside `rag/venv/` | Delete. | Generated bytecode only: `bench/__pycache__`, `localchat_tui/__pycache__`, `localchat_tui/widgets/__pycache__`, `rag/__pycache__`. No source import path depends on these directories. |
| Hidden VCS metadata inside `rag/corpus/` such as `.git`, `.github`, `.gitignore` | Delete. | Current ingest skips hidden paths for markdown sources: `rag/chunker.py:93-97`. MITRE ingest reads only specific JSON attack-pattern directories: `rag/mitre_loader.py:5-9,40-56`. These hidden metadata directories/files are not on runtime or ingest paths. |
| Non-content build files inside vendored corpus clones such as `mkdocs.yml`, `package.json`, `requirements.txt` | Delete. | Non-MITRE ingest reads markdown only: `rag/chunker.py:93-97`. MITRE ingest reads only JSON attack-pattern data: `rag/mitre_loader.py:5-9,40-56`. Files like `rag/corpus/CheatSheetSeries/mkdocs.yml`, `package.json`, `requirements.txt`, and `rag/corpus/PayloadsAllTheThings/mkdocs.yml` are outside those read paths. |

## 5. Code Cleanup Inside Kept Files

These are not directory removals; they are code trims that should happen in Phase 2.

| File | Proposed change | Concrete evidence | Risk |
| --- | --- | --- | --- |
| `localchat_tui/backend.py` | Remove `MockBackendAdapter`. | The real app constructs `HackerLMBackendAdapter`: `localchat_tui/main.py:7-8`. `MockBackendAdapter` lives only as leftover prototype code in `localchat_tui/backend.py:280-394` and is not imported anywhere else. | Low. |
| `hacker_lm` | Remove legacy REPL help text if `rag/retrieve.py` is quarantined. | Current help still advertises `rag/venv/bin/python -m rag.retrieve`: `hacker_lm:19-23`. | Low. |
| `README.md` | Remove references to bench and old REPL if quarantined; keep only the TUI + worker + service path. | Current README still documents the old CLI path: `README.md:53-57`. | Low. |
| `rag/requirements.txt` | Remove unused dependencies after quarantine decisions. | `rank-bm25` is present in `rag/requirements.txt:1-7` but current runtime uses `bm25s` in `rag/service.py:114-120`; `rich` is only used by legacy REPL UI in `rag/cli_ui.py:8-13`. | Low to medium; must be done only after legacy REPL is quarantined. |

## 6. Uncertain Or Keep-For-Now

These items are off the hot path or imperfect, but I do not have enough reason to strip them in the first cleanup pass.

| Path | Current judgment | Why not remove yet |
| --- | --- | --- |
| `rag/venv/` internals | Keep. | It makes the repo heavier, but the launcher and worker hard-require this exact environment path today: `hacker_lm:9,32-38`, `localchat_tui/backend.py:64,159-165`. Reworking this would change product behavior. |
| `rag/ingest.py`, `rag/chunker.py`, `rag/mitre_loader.py` | Keep. | They are not startup-path, but without them the repo loses the ability to rebuild or evolve the local index from source corpora. |
| Markdown content inside vendored corpora, including upstream `README.md` and `LICENSE*.md` where present | Keep for now. | Non-MITRE ingest reads `*.md` recursively: `rag/chunker.py:93-97`. Removing markdown content changes future index rebuild behavior, so this needs a deliberate corpus-curation pass, not a first strip pass. |
| Duplicate Ollama startup checks in launcher and worker | Keep behavior for now. | Both `hacker_lm` and `rag/tui_worker.py` call runtime checks: `hacker_lm:37`, `rag/tui_worker.py:29-30`. This looks redundant, but changing it affects cold-start/runtime behavior. |

## 7. Main Risks

1. Quarantining `rag/retrieve.py` and `rag/cli_ui.py` removes a still-functional secondary interface. That matches the stated goal, but it narrows non-TUI smoke options.
2. Quarantining `bench/` removes historical benchmark code and results from the active tree. This is intentional, but any future performance work would start from the quarantined copy.
3. Corpus cleanup must avoid deleting actual source markdown or MITRE attack-pattern JSON used by ingest. Only hidden VCS metadata and clearly unused build files should be touched in the first pass.
4. `rag/venv/` is currently part of the runnable product contract. A truly source-only repo would be leaner, but changing that now is higher risk than this strip pass should take.

## 8. Proposed Phase 2 Order

1. Create `_removed_from_product/`.
2. Move `bench/`, legacy docs, legacy tool-local config, legacy REPL files, and `Modelfile.bak` into quarantine.
3. Remove safe junk: empty `.codex`, repo code `__pycache__`, corpus VCS/build metadata, unused `bm25_corpus.pkl`.
4. Trim dead code from kept files, especially `MockBackendAdapter`.
5. Rewrite `README.md` to describe only the kept product.
6. Add `PRODUCT_STRUCTURE.md` to replace scattered historical notes with one current product map.
7. Run lightweight validation only after cleanup.

## 9. Verification Targets For Phase 4

After cleanup, verify at minimum:

- `./hacker_lm --help` still works.
- `python3 -m localchat_tui` import path still resolves when Textual is available.
- `rag/venv/bin/python -m rag.tui_worker --help` still resolves.
- Backend imports still work: `rag.service`, `rag.runtime`, `rag.tui_worker`.
- Required runtime files still exist:
  - `rag/venv/bin/python`
  - `rag/chroma_db/chroma.sqlite3`
  - `rag/chroma_db/bm25s_index/`
  - `rag/chroma_db/bm25_meta.pkl`
  - `Modelfile`
  - `requirements-tui.txt`

## 10. Summary

Planned end state:
- Keep the product spine: `hacker_lm -> localchat_tui -> rag.tui_worker -> rag.service -> Ollama + rag/chroma_db`.
- Keep only the supporting materials needed to rebuild the alias, refresh the corpus, and maintain the live retrieval stack.
- Quarantine legacy/secondary systems instead of deleting them blindly.
- Remove safe junk and dead code only where the evidence is concrete.
