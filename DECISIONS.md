# DECISIONS

Dated, one-line rationale for non-obvious choices made during the build. Orchestrator syncs important entries into memory periodically.

## 2026-05-15

- **Eval scoring is deterministic-only for v2 baseline; LLM-as-judge deferred** — the harness must be cheap and reproducible so every change can be A/B'd without judge-cost or judge-noise. LLM-judge can land as a fourth optional score later.
- **`retrieval_score = 0.7 * path_recall + 0.3 * substring_recall`** — path matches are stricter (less false-positive prone) than free-text substring presence, so they dominate the blend. Substring recall stays as a softer secondary signal that survives corpus path churn between re-ingestions.
- **`questions.jsonl` is the schema, not a pinned chunk-ID list** — we don't pre-commit to specific Chroma chunk IDs because re-ingestion will renumber them. Gold signals are substring-based (path fragments + key strings + facts) so the eval survives corpus rebuilds.
- **`gold_chunk_paths` matches via substring within `meta.rel_path`, not exact equality** — exact path equality breaks when HackTricks (or any upstream) restructures. Substring-on-rel_path keeps recall stable across pulls.
- **Eval harness re-execs under `rag/venv/bin/python`** — instead of asking the user to remember which Python to use. Detection uses `sys.prefix` against the venv root, not `Path.resolve()`, because the venv python in this project is a symlink chain into a mise-managed system Python; resolved paths are identical and would skip the re-exec silently.
- **Strictly-additive method `RetrieveService.retrieve_top_hits()`** — exposes the raw reranked hits to the eval runner without changing `stream_query` behavior or event shape. Pays a duplicate retrieval cost per eval question (milliseconds) to keep the existing TUI path untouched.
- **`<think>` defaults to OFF in eval runs** — the v1 model emits long reasoning traces that bloat wall-clock for marginal scoring signal. Real baseline can be re-run with `--think on` for a separate result file if reasoning-mode quality is the question being asked.
- **Corpora not vendored, no submodules** — `rag/corpus/` is gitignored. `CORPUS_SETUP.md` documents `git clone --depth=1` for the four upstream repos. Submodules would tie our repo's history to theirs and complicate pulls.
