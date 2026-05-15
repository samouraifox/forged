# PRODUCT_STRUCTURE

This repo now keeps only the active `hacker_lm` product path plus the minimum supporting files needed to run it, maintain it, and evolve it safely.

## What Remains

- `hacker_lm`
  - Canonical launcher from the repo root.
- `localchat_tui/`
  - Active Textual frontend, state, styling, and widgets.
- `rag/runtime.py`
  - Ollama startup and runtime verification.
- `rag/tui_worker.py`
  - Structured JSON worker launched from `rag/venv`.
- `rag/service.py`
  - Retrieval, reranking, prompt construction, and model calls.
- `rag/chroma_db/`
  - Live Chroma + BM25 index used by the product.
- `rag/ingest.py`, `rag/chunker.py`, `rag/mitre_loader.py`, `rag/corpus/`
  - Kept maintenance path for rebuilding the local index.
- `Modelfile`
  - Source of truth for the `hacker-guide` alias.
- `requirements-tui.txt`, `rag/requirements.txt`
  - Minimal dependency manifests for the kept frontend and backend paths.

## Startup Flow

1. Run `./hacker_lm` from the repo root.
2. The launcher checks `rag/venv/bin/python` and runs `rag.runtime --ensure-ollama`.
3. The launcher starts `python3 -m localchat_tui` or falls back to `uv run --with textual python -m localchat_tui`.
4. The Textual app constructs `HackerLMBackendAdapter` and calls `startup()`.
5. The adapter starts `rag/venv/bin/python -u -m rag.tui_worker --db rag/chroma_db`.
6. `rag.tui_worker` ensures Ollama is running, initializes `RetrieveService`, and streams structured events back to the TUI.
7. `RetrieveService` loads Chroma, `bm25s_index`, `bm25_meta.pkl`, the reranker, and queries the `hacker-guide` model alias.

## Important Files And Folders

- [hacker_lm](/home/samouraifox/Work/Projects/llm-weapon-v2/hacker_lm)
  - Entry point users should run.
- [localchat_tui/main.py](/home/samouraifox/Work/Projects/llm-weapon-v2/localchat_tui/main.py)
  - Frontend entry point.
- [localchat_tui/app.py](/home/samouraifox/Work/Projects/llm-weapon-v2/localchat_tui/app.py)
  - TUI lifecycle and interaction flow.
- [localchat_tui/backend.py](/home/samouraifox/Work/Projects/llm-weapon-v2/localchat_tui/backend.py)
  - Real frontend-to-worker bridge.
- [rag/tui_worker.py](/home/samouraifox/Work/Projects/llm-weapon-v2/rag/tui_worker.py)
  - Structured backend transport.
- [rag/service.py](/home/samouraifox/Work/Projects/llm-weapon-v2/rag/service.py)
  - Core retrieval and generation logic.
- [rag/runtime.py](/home/samouraifox/Work/Projects/llm-weapon-v2/rag/runtime.py)
  - Ollama runtime management.
- [rag/ingest.py](/home/samouraifox/Work/Projects/llm-weapon-v2/rag/ingest.py)
  - Index rebuild path. Run it from `rag/`, not from the repo root.
- [rag/chroma_db](/home/samouraifox/Work/Projects/llm-weapon-v2/rag/chroma_db)
  - Runtime retrieval data.
- [Modelfile](/home/samouraifox/Work/Projects/llm-weapon-v2/Modelfile)
  - Alias definition for `hacker-guide`.
- [_removed_from_product](/home/samouraifox/Work/Projects/llm-weapon-v2/_removed_from_product)
  - Quarantine area for legacy or non-primary paths kept for reference.

## Intentionally Removed From The Active Surface

- `bench/`
  - Quarantined because it is not part of the live launch or runtime path and it targets an older retrieval interface.
- `rag/retrieve.py` and `rag/cli_ui.py`
  - Quarantined because the supported interface is now the Textual app plus `rag.tui_worker`.
- `CONTEXT_FOR_GPT.md`, `upgrade-paths.txt`, `.claude/settings.local.json`, `Modelfile.bak`
  - Quarantined because they are historical notes, stale tool-local config, or backup artifacts, not active product files.
- `rag/chroma_db/bm25_corpus.pkl`
  - Quarantined because the active service reads `bm25s_index` and `bm25_meta.pkl`, not this file.
- Repo bytecode caches and corpus VCS/build metadata
  - Deleted as non-runtime noise.

## Known Boundaries

- `rag/venv/` remains on purpose in this pass because the launcher and backend adapter still require that exact path.
- Markdown corpus content and license/provenance files were kept.
- `_removed_from_product/` is archival, not part of the supported product path.
