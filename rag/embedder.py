"""Qwen3-Embedding-0.6B via OpenVINO, sentence-transformers-compatible interface.

Replaces nomic-embed-text (Ollama) as the embedding backend. Implements the
exact pooling, prompt-format, and normalization protocol from the Qwen3-Embedding
model card:

- Tokenizer with padding_side='left' (last-token pooling requires it)
- Queries are wrapped with: "Instruct: <task>\\nQuery: <text>"
- Documents are encoded raw (no prefix)
- Pooling: last-token hidden state, left-padding-aware
- Output: L2-normalized 1024-dim float vectors

Device selection: tries QWEN3_EMBED_DEVICE (default GPU) first; falls back to
CPU if iGPU init fails. On Lunar Lake / Arc 140V this typically means CPU
unless intel-compute-runtime is installed at the OS level.

USE_QWEN3_EMBEDDING (default True) gates the new path; setting it to "0" or
"false" routes through a legacy ollama nomic-embed-text fallback. The fallback
exists for one phase only and is scheduled for removal in Phase 3d.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

DEFAULT_MODEL_DIR = Path.home() / "models" / "openvino" / "qwen3-embedding-0.6b-int8"
MODEL_DIR = Path(os.environ.get("QWEN3_EMBED_DIR", str(DEFAULT_MODEL_DIR)))

USE_QWEN3_EMBEDDING = os.environ.get("USE_QWEN3_EMBEDDING", "1").strip().lower() not in {
    "0", "false", "no", "off", ""
}

# Tight to our retrieval task; the model card says to write a short instruction
# that captures the user-intent and corpus shape.
QUERY_TASK = (
    "Given a cybersecurity question, retrieve passages from offensive security, "
    "vulnerability research, and threat-intelligence references that answer it."
)

MAX_LEN = 2048  # The chunker caps chunks at ~900 tokens; 2048 is generous
# headroom for queries with the Instruct prefix. Capping aggressively keeps
# the per-batch attention scratch space (O(L^2) per layer) within the Arc
# 140V iGPU memory budget. Qwen3 supports up to 32K; we are not using it.
EMBED_DIM = 1024

_model = None
_tokenizer = None
_device: str | None = None


def _qwen3_lazy_init() -> str:
    """Lazy-load the OpenVINO model + tokenizer. Returns the effective device.

    Tries QWEN3_EMBED_DEVICE (default GPU). On failure (typically missing
    intel-compute-runtime on Lunar Lake), falls back to CPU and prints once.
    """
    global _model, _tokenizer, _device
    if _model is not None:
        return _device  # type: ignore[return-value]

    from optimum.intel import OVModelForFeatureExtraction
    from transformers import AutoTokenizer

    if not MODEL_DIR.exists():
        raise RuntimeError(
            f"Qwen3 OpenVINO model dir not found at {MODEL_DIR}. "
            f"Run: optimum-cli export openvino --model Qwen/Qwen3-Embedding-0.6B "
            f"--task feature-extraction --weight-format int8 {MODEL_DIR}"
        )

    _tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), padding_side="left")

    requested = os.environ.get("QWEN3_EMBED_DEVICE", "GPU").upper()
    try:
        _model = OVModelForFeatureExtraction.from_pretrained(str(MODEL_DIR), device=requested)
        _device = requested
    except Exception as exc:
        if requested == "CPU":
            raise
        print(
            f"[embedder] {requested} init failed ({type(exc).__name__}: {exc}); "
            f"falling back to CPU",
            flush=True,
        )
        _model = OVModelForFeatureExtraction.from_pretrained(str(MODEL_DIR), device="CPU")
        _device = "CPU"

    return _device  # type: ignore[return-value]


def _last_token_pool(last_hidden_states, attention_mask):
    """Left-padding-aware last-token pool, per the model card."""
    import torch

    left_padding = bool(attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    sequence_lengths = attention_mask.sum(dim=1) - 1
    batch_size = last_hidden_states.shape[0]
    return last_hidden_states[
        torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths
    ]


def _format_query(text: str) -> str:
    return f"Instruct: {QUERY_TASK}\nQuery: {text}"


def _qwen3_embed_texts(texts: list[str], *, is_query: bool) -> list[list[float]]:
    import torch
    import torch.nn.functional as F

    _qwen3_lazy_init()
    if is_query:
        texts = [_format_query(t) for t in texts]

    inputs = _tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=MAX_LEN,
        return_tensors="pt",
    )
    outputs = _model(**inputs)
    pooled = _last_token_pool(outputs.last_hidden_state, inputs["attention_mask"])
    normed = F.normalize(pooled, p=2, dim=1)
    return normed.detach().cpu().to(torch.float32).numpy().tolist()


def _ollama_fallback_embed(texts: list[str], *, is_query: bool) -> list[list[float]]:
    """Legacy nomic-embed-text path. Scheduled for removal in Phase 3d.

    Mirrors the original two call patterns:
      - query side (was @lru_cache + ollama.embeddings(prompt=))
      - doc side (was ollama.embed(input=[...]) batched with truncation)
    The `is_query` flag is informational only here — nomic-embed-text used no
    distinct query/doc routing, so both code paths converge.
    """
    del is_query  # nomic did not differentiate
    import ollama

    MAX_CHARS = 1500
    NUM_CTX = 8192
    safe = [t[:MAX_CHARS] for t in texts]
    response = ollama.embed(model="nomic-embed-text", input=safe, options={"num_ctx": NUM_CTX})
    return list(response["embeddings"])


def embed_texts(texts: Iterable[str], *, is_query: bool = False) -> list[list[float]]:
    """Encode an iterable of texts. Returns one list[float] per input.

    Output dim is 1024 under Qwen3 (USE_QWEN3_EMBEDDING=1, default) or 768
    under the ollama fallback. Mixing dims across a single Chroma collection
    will fail at write/query time — set the flag before the very first
    ingest pass and do not flip it mid-corpus.
    """
    text_list = list(texts)
    if not text_list:
        return []
    if USE_QWEN3_EMBEDDING:
        return _qwen3_embed_texts(text_list, is_query=is_query)
    return _ollama_fallback_embed(text_list, is_query=is_query)


def active_backend() -> dict:
    """Diagnostic — used in init status lines."""
    if not USE_QWEN3_EMBEDDING:
        return {"backend": "ollama-nomic-embed-text", "dim": 768}
    return {
        "backend": "qwen3-embedding-0.6b-openvino",
        "device": _device or "(not yet initialized)",
        "model_dir": str(MODEL_DIR),
        "dim": EMBED_DIM,
        "max_len": MAX_LEN,
    }
