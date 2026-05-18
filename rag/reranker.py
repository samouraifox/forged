"""Qwen3-Reranker-0.6B via OpenVINO, CrossEncoder-compatible interface.

Replaces cross-encoder/ms-marco-MiniLM-L-6-v2 (sentence-transformers,
PyTorch CPU, 23M params, classifier head) with Qwen3-Reranker-0.6B
(OpenVINO int8, 600M params, CausalLM with yes/no token-logit extraction).

Why CausalLM and not text-classification: Qwen3-Reranker has no classifier
head. The model card protocol wraps each (query, doc) pair in a chat-template
prompt with a 'yes/no' answer constraint, runs a single forward pass, and
extracts the logits for the 'yes' and 'no' tokens at the final position.
Relevance score = softmax([no_logit, yes_logit])[1].

Exposes a `.predict(pairs)` method matching the sentence-transformers
CrossEncoder interface (list of (query, doc) tuples → list of scores in
the same order), so the existing rag.service.rerank() call site can use
this class as a drop-in replacement for `CrossEncoder(...)`.

Device selection: GPU first (Arc 140V iGPU via OpenVINO), CPU fallback.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_MODEL_DIR = Path.home() / "models" / "openvino" / "qwen3-reranker-0.6b-int8"
MODEL_DIR = Path(os.environ.get("QWEN3_RERANKER_DIR", str(DEFAULT_MODEL_DIR)))

USE_QWEN3_RERANKER = os.environ.get("USE_QWEN3_RERANKER", "1").strip().lower() not in {
    "0", "false", "no", "off", ""
}

# Same task-tight instruction shape used for the embedder; keeps the two
# stages reading from the same "what is this corpus about" intent.
RERANKER_TASK = (
    "Given a cybersecurity question, judge whether the passage helps answer it. "
    "Treat partial-answer passages with operator-relevant detail as relevant."
)

# Chat-template scaffolding per the Qwen3-Reranker model card.
_SYSTEM = (
    "Judge whether the Document meets the requirements based on the Query "
    'and the Instruct provided. Note that the answer can only be "yes" or "no".'
)
_PREFIX = f"<|im_start|>system\n{_SYSTEM}<|im_end|>\n<|im_start|>user\n"
_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

# Attention activation scratch scales as B × heads × L² × 2 bytes per layer.
# Qwen3-Reranker has 28 layers × 14 heads; at B=8, L=2048 that pre-allocates
# ~26 GB on the OpenVINO GPU plugin (UMA: comes out of system RAM, owned by
# i915, invisible to ps RSS). At B=4, L=1024 it is ~3.3 GB. The chunker caps
# bodies at ~900 approx-tokens (TARGET=600, MAX=900); the reranker prompt
# wrapper (instruct + chat scaffolding) adds ~100 tokens, leaving headroom
# inside the 1024 budget. See LOGS/day-3.5-reranker-budget-fix.md for the
# kernel-driver-owned UMA memory diagnosis and the activation-pool math.
BATCH = 4
MAX_LEN = 1024

_model = None
_tokenizer = None
_yes_id: int | None = None
_no_id: int | None = None
_device: str | None = None


def _lazy_init() -> str:
    """Load model + tokenizer once. GPU first, CPU fallback. Returns active device."""
    global _model, _tokenizer, _yes_id, _no_id, _device
    if _model is not None:
        return _device  # type: ignore[return-value]

    from optimum.intel import OVModelForCausalLM
    from transformers import AutoTokenizer

    if not MODEL_DIR.exists():
        raise RuntimeError(
            f"Qwen3 reranker OpenVINO model dir not found at {MODEL_DIR}. "
            f"Run: optimum-cli export openvino --model Qwen/Qwen3-Reranker-0.6B "
            f"--task text-generation --weight-format int8 {MODEL_DIR}"
        )

    # `fix_mistral_regex=True` — same case-boundary fix applied to the embedder
    # tokenizer; the Qwen3-Reranker tokenizer.json has the same broken regex.
    # `truncation_side="left"` is required for correctness at any MAX_LEN tight
    # enough to cut: the yes/no logits are read from position -1, which is the
    # `<|im_start|>assistant\n<think>\n\n</think>\n\n` suffix. Right-truncation
    # (the default) drops that suffix and silently reads logits from a random
    # mid-document token, so scores drift in unpredictable ways. Left-truncation
    # drops doc-start tokens instead, preserving the answer-extraction position.
    _tokenizer = AutoTokenizer.from_pretrained(
        str(MODEL_DIR),
        padding_side="left",
        truncation_side="left",
        fix_mistral_regex=True,
    )
    _yes_id = _tokenizer.convert_tokens_to_ids("yes")
    _no_id = _tokenizer.convert_tokens_to_ids("no")

    requested = os.environ.get("QWEN3_RERANKER_DEVICE", "GPU").upper()
    try:
        _model = OVModelForCausalLM.from_pretrained(str(MODEL_DIR), device=requested, use_cache=False)
        _device = requested
    except Exception as exc:
        if requested == "CPU":
            raise
        print(
            f"[reranker] {requested} init failed ({type(exc).__name__}: {exc}); "
            f"falling back to CPU",
            flush=True,
        )
        _model = OVModelForCausalLM.from_pretrained(str(MODEL_DIR), device="CPU")
        _device = "CPU"

    return _device  # type: ignore[return-value]


def _format(query: str, doc: str) -> str:
    body = (
        f"<Instruct>: {RERANKER_TASK}\n"
        f"<Query>: {query}\n"
        f"<Document>: {doc}"
    )
    return f"{_PREFIX}{body}{_SUFFIX}"


def _score_batch(prompts: list[str]) -> list[float]:
    import torch

    inputs = _tokenizer(
        prompts,
        padding=True,
        truncation=True,
        max_length=MAX_LEN,
        return_tensors="pt",
    )
    outputs = _model(**inputs)
    logits = outputs.logits  # shape: [B, L, V]
    # left-padding => the last position is the most-recent token for every row
    last = logits[:, -1, :]
    yes_logits = last[:, _yes_id]
    no_logits = last[:, _no_id]
    # softmax([no, yes])[..., 1] = P(yes)
    stacked = torch.stack([no_logits, yes_logits], dim=1)
    probs = torch.nn.functional.softmax(stacked, dim=1)
    return probs[:, 1].detach().cpu().to(torch.float32).numpy().tolist()


class Qwen3Reranker:
    """CrossEncoder-compatible reranker. Use as a drop-in for sentence_transformers.CrossEncoder."""

    def __init__(self, lazy: bool = True):
        if not lazy:
            _lazy_init()

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        _lazy_init()
        prompts = [_format(q, d) for q, d in pairs]
        scores: list[float] = []
        for i in range(0, len(prompts), BATCH):
            scores.extend(_score_batch(prompts[i : i + BATCH]))
        return scores


def active_backend() -> dict:
    if not USE_QWEN3_RERANKER:
        return {"backend": "cross-encoder/ms-marco-MiniLM-L-6-v2", "via": "sentence-transformers"}
    return {
        "backend": "qwen3-reranker-0.6b-openvino",
        "device": _device or "(not yet initialized)",
        "model_dir": str(MODEL_DIR),
        "batch": BATCH,
        "max_len": MAX_LEN,
    }
