"""Single source of truth for the v2 stack defaults.

Anything that needs a default DB path, collection name, or model identifier
should import from this module. Per-script CLI overrides (--db, --collection,
USE_QWEN3_EMBEDDING=0, etc.) are still respected — these are only the
fallback values applied when no override is provided.

v1 (DeepSeek-R1 abliterated + nomic-embed + ms-marco-MiniLM, collection
'security' at rag/chroma_db) is decommissioned. No fallback path that
auto-tries v1 then v2 exists by design; the v1 corpus on disk is preserved
for archive replay only and must be selected via explicit args.
"""
from __future__ import annotations

from pathlib import Path

_RAG_DIR = Path(__file__).resolve().parent

# Chroma corpus — Phase 3.5+2 production
V2_DB_PATH = str(_RAG_DIR / "chroma_db_cve_full")
V2_COLLECTION = "forged_v2_qwen3_emb_cve_full"

# Embedder + reranker — actual loading routes through rag/embedder.py and
# rag/reranker.py (env-var gated). These constants are display labels only.
V2_EMBEDDER_MODEL = "Qwen3-Embedding-0.6B"
V2_RERANKER_MODEL = "Qwen3-Reranker-0.6B"

# Generation backend
V2_LLM_BACKEND = "llama-server"
V2_LLM_MODEL = "hermes-4-14b"
V2_LLM_DISPLAY_NAME = "Hermes-4-14B (Q6_K, llama-server)"
V2_LLM_BASE_URL = "http://127.0.0.1:8080/v1"
