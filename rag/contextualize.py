"""Anthropic Contextual Retrieval — prepend per-chunk context before embedding.

For each chunk in the source Chroma collection, ask Qwen3-4B to produce a
50-100 token summary that situates the chunk within its parent document.
The contextualized text (context + separator + original chunk text) is
embedded with Qwen3-Embedding-0.6B and written into a new collection,
along with a fresh BM25 snapshot.

Document reconstruction
-----------------------
The source corpus directory (`rag/corpus/`) is empty (gitignored), so we
cannot read the original markdown files. We instead reconstruct each
"document" by grouping chunks on their `rel_path` metadata field. The
`source` field is degenerate (only 4 values — hacktricks, mitre, owasp,
payloads — i.e. corpus names, not documents); `rel_path` is the true
per-document key with 2,300 unique values across the 14,308 chunks.

Chunk ordering within a rel_path follows the trailing numeric suffix of
the chunk_id (`{source}::{rel_path}::{idx}`). The v1 chunker occasionally
emitted duplicate suffixes (e.g. CONTRIBUTING.md has two chunks with
idx=0); ordering across duplicates is stable-but-arbitrary in this script.

If the reconstructed document exceeds ~80,000 characters (~32K tokens with
prompt-template headroom), we fall back to a ±10-chunk neighborhood
centered on the target chunk. The biggest single document in the corpus
has 101 chunks; only ~5 documents exceed the cap.
"""

from __future__ import annotations

import argparse
import os
import pickle
import re
import time
from collections import defaultdict
from pathlib import Path

import chromadb
from tqdm import tqdm

from embedder import embed_texts, active_backend as embed_backend

TOKEN_RE = re.compile(r"\w+")
SUFFIX_RE = re.compile(r".*::(\d+)$")
BATCH = 16
MAX_DOC_CHARS = 80_000
NEIGHBORHOOD = 10
CONTEXT_SEPARATOR = "\n\n---\n\n"

DEFAULT_QWEN3_4B_DIR = Path.home() / "models" / "openvino" / "qwen3-4b-int4"
QWEN3_4B_DIR = Path(os.environ.get("QWEN3_4B_DIR", str(DEFAULT_QWEN3_4B_DIR)))

# Anthropic Contextual Retrieval prompt — verbatim from their cookbook,
# with the operator-mentor instruction line tightened for our domain.
PROMPT_TEMPLATE = """<document>
{document}
</document>

Here is the chunk we want to situate within the whole document:
<chunk>
{chunk}
</chunk>

Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

_gen_model = None
_gen_tokenizer = None
_gen_device: str | None = None


def _gen_lazy_init() -> str:
    global _gen_model, _gen_tokenizer, _gen_device
    if _gen_model is not None:
        return _gen_device  # type: ignore[return-value]

    from optimum.intel import OVModelForCausalLM
    from transformers import AutoTokenizer

    if not QWEN3_4B_DIR.exists():
        raise RuntimeError(
            f"Qwen3-4B OpenVINO dir not found at {QWEN3_4B_DIR}. "
            f"Run: optimum-cli export openvino --model Qwen/Qwen3-4B "
            f"--task text-generation-with-past --weight-format int4 {QWEN3_4B_DIR}"
        )

    _gen_tokenizer = AutoTokenizer.from_pretrained(
        str(QWEN3_4B_DIR), padding_side="left", fix_mistral_regex=True
    )
    requested = os.environ.get("QWEN3_4B_DEVICE", "GPU").upper()
    try:
        _gen_model = OVModelForCausalLM.from_pretrained(str(QWEN3_4B_DIR), device=requested)
        _gen_device = requested
    except Exception as exc:
        if requested == "CPU":
            raise
        print(
            f"[contextualize] {requested} init failed ({type(exc).__name__}: {exc}); "
            f"falling back to CPU",
            flush=True,
        )
        _gen_model = OVModelForCausalLM.from_pretrained(str(QWEN3_4B_DIR), device="CPU")
        _gen_device = "CPU"

    return _gen_device  # type: ignore[return-value]


def _chunk_idx(chunk_id: str) -> int:
    m = SUFFIX_RE.match(chunk_id)
    return int(m.group(1)) if m else 10**9


def _group_by_rel_path(ids: list[str], docs: list[str], metas: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for cid, doc, meta in zip(ids, docs, metas):
        rp = meta.get("rel_path", "(unknown)")
        groups[rp].append({"id": cid, "doc": doc, "meta": meta, "idx": _chunk_idx(cid)})
    for rp in groups:
        groups[rp].sort(key=lambda c: (c["idx"], c["id"]))
    return groups


def _reconstruct_document(group: list[dict], target_chunk_id: str) -> str:
    full_text = "\n\n".join(c["doc"] for c in group)
    if len(full_text) <= MAX_DOC_CHARS:
        return full_text

    target_pos = next(
        (i for i, c in enumerate(group) if c["id"] == target_chunk_id),
        len(group) // 2,
    )
    start = max(0, target_pos - NEIGHBORHOOD)
    end = min(len(group), target_pos + NEIGHBORHOOD + 1)
    return "\n\n".join(c["doc"] for c in group[start:end])


def _build_chat_prompt(document: str, chunk: str) -> str:
    user_content = PROMPT_TEMPLATE.format(document=document, chunk=chunk)
    # Qwen3 emits a <think>...</think> reasoning trace by default that
    # eats the entire max_new_tokens budget on short-output tasks like
    # context summarization. enable_thinking=False is the documented
    # Qwen3 chat-template kwarg to suppress it. (Equivalent to the
    # `<think>\n\n</think>` assistant prefix used in the reranker.)
    return _gen_tokenizer.apply_chat_template(
        [{"role": "user", "content": user_content}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )


def _generate_context(document: str, chunk: str, max_new_tokens: int) -> str:
    import torch

    prompt = _build_chat_prompt(document, chunk)
    inputs = _gen_tokenizer(prompt, return_tensors="pt", truncation=True, max_length=30_000)
    out = _gen_model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=_gen_tokenizer.eos_token_id,
    )
    gen_tokens = out[0][inputs["input_ids"].shape[1] :]
    text = _gen_tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
    # Strip Qwen think tags if the model emits them despite chat template
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-db", required=True)
    ap.add_argument("--src-collection", required=True)
    ap.add_argument("--dst-db", required=True)
    ap.add_argument("--dst-collection", required=True)
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="Stop after N chunks (smoke testing)")
    ap.add_argument("--max-new-tokens", type=int, default=100)
    ap.add_argument("--save-contexts", default=None, help="Optional JSONL path: write {id, context} per chunk")
    args = ap.parse_args()

    print(f"[contextualize] generator model dir: {QWEN3_4B_DIR}", flush=True)
    print(f"[contextualize] embedder backend: {embed_backend()}", flush=True)

    src_client = chromadb.PersistentClient(path=args.src_db)
    src_col = src_client.get_collection(args.src_collection)
    src_data = src_col.get(include=["documents", "metadatas"])
    ids = src_data["ids"]
    docs = src_data["documents"]
    metas = src_data["metadatas"]
    print(f"[src] {args.src_db} :: {args.src_collection} has {len(ids)} chunks", flush=True)

    groups = _group_by_rel_path(ids, docs, metas)
    print(f"[group] {len(groups)} unique rel_paths", flush=True)

    if args.limit is not None:
        ids = ids[: args.limit]
        docs = docs[: args.limit]
        metas = metas[: args.limit]

    dst_client = chromadb.PersistentClient(path=args.dst_db)
    if args.reset:
        try:
            dst_client.delete_collection(args.dst_collection)
            print(f"[dst] dropped {args.dst_collection}", flush=True)
        except Exception:
            pass
    dst_col = dst_client.get_or_create_collection(args.dst_collection, metadata={"hnsw:space": "cosine"})

    existing = set(dst_col.get(include=[])["ids"]) if dst_col.count() else set()
    pending = [i for i, cid in enumerate(ids) if cid not in existing]
    print(f"[dst] {args.dst_db} :: {args.dst_collection} has {len(existing)} chunks; {len(pending)} pending", flush=True)

    _gen_lazy_init()
    print(f"[contextualize] generator on device: {_gen_device}", flush=True)

    contexts_handle = open(args.save_contexts, "a") if args.save_contexts else None
    contextualized_texts: dict[str, str] = {}
    rel_path_for: dict[str, str] = {ids[i]: metas[i].get("rel_path", "(unknown)") for i in pending}
    print(f"[gen] generating contexts for {len(pending)} chunks...", flush=True)

    gen_t0 = time.perf_counter()
    for idx_pos, i in enumerate(tqdm(pending, desc="gen-context")):
        cid = ids[i]
        chunk_text = docs[i]
        rp = rel_path_for[cid]
        group = groups[rp]
        document = _reconstruct_document(group, cid)
        try:
            context = _generate_context(document, chunk_text, args.max_new_tokens)
        except Exception as e:
            print(f"\n[skip-gen] {cid}: {e}", flush=True)
            context = ""
        ctxed = f"{context}{CONTEXT_SEPARATOR}{chunk_text}" if context else chunk_text
        contextualized_texts[cid] = ctxed
        if contexts_handle:
            import json
            contexts_handle.write(json.dumps({"id": cid, "context": context}) + "\n")
            contexts_handle.flush()
    if contexts_handle:
        contexts_handle.close()
    gen_dt = time.perf_counter() - gen_t0
    print(f"[gen] context generation done in {gen_dt:.0f}s ({len(pending)/max(gen_dt, 1e-6):.2f} chunks/sec)", flush=True)

    # Embed contextualized texts in BATCH-sized groups.
    print(f"[embed] embedding {len(contextualized_texts)} contextualized chunks...", flush=True)
    pending_ids = list(contextualized_texts.keys())
    embed_t0 = time.perf_counter()
    for start in tqdm(range(0, len(pending_ids), BATCH), desc="embed+add"):
        batch_ids = pending_ids[start : start + BATCH]
        batch_texts = [contextualized_texts[c] for c in batch_ids]
        try:
            vecs = embed_texts(batch_texts, is_query=False)
        except Exception as e:
            print(f"\n[embed-fallback] {e}", flush=True)
            vecs = []
            for t in batch_texts:
                try:
                    vecs.append(embed_texts([t], is_query=False)[0])
                except Exception as e2:
                    print(f"\n[skip-embed] {e2}", flush=True)
                    vecs.append(None)
        keep = [(cid, v, t) for cid, v, t in zip(batch_ids, vecs, batch_texts) if v is not None]
        if not keep:
            continue
        kept_metas = []
        for cid, _, _ in keep:
            orig_idx = ids.index(cid)
            m = dict(metas[orig_idx])
            m["context_applied"] = True
            kept_metas.append(m)
        dst_col.add(
            ids=[cid for cid, _, _ in keep],
            embeddings=[v for _, v, _ in keep],
            documents=[t for _, _, t in keep],
            metadatas=kept_metas,
        )
    embed_dt = time.perf_counter() - embed_t0
    print(f"[embed] embedding done in {embed_dt:.0f}s", flush=True)

    import bm25s
    all_data = dst_col.get(include=["documents", "metadatas"])
    print(f"[bm25] tokenizing {len(all_data['documents'])} contextualized docs...", flush=True)
    tokenized = [tokenize(d) for d in all_data["documents"]]
    bm25 = bm25s.BM25()
    bm25.index(tokenized)
    bm25.save(Path(args.dst_db) / "bm25s_index")
    with open(Path(args.dst_db) / "bm25_meta.pkl", "wb") as h:
        pickle.dump(
            {"ids": all_data["ids"], "docs": all_data["documents"], "metas": all_data["metadatas"]},
            h,
        )

    print(
        f"[done] {args.dst_db} :: {args.dst_collection} collection_size={dst_col.count()} "
        f"bm25_saved gen_t={gen_dt:.0f}s embed_t={embed_dt:.0f}s",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
