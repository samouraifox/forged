"""Build a partial-context Chroma collection at the current checkpoint.

For each of the 14,308 chunks in forged_v2_qwen3_emb:
- If the chunk has a generated context (in contexts.jsonl): re-embed the
  contextualized text (`{context}\\n\\n---\\n\\n{original}`) with Qwen3-Embedding,
  store with `context_applied=True`.
- If the chunk has no generated context yet: keep the existing embedding
  byte-identical, store with `context_applied=False`.

Builds a fresh BM25 index over the partial-context corpus (where
contextualized text is used when available, original text otherwise).
"""

from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
from pathlib import Path

# Ensure rag/ is on sys.path so we can import embedder when run from rag/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from tqdm import tqdm

from embedder import embed_texts

TOKEN_RE = re.compile(r"\w+")
SEPARATOR = "\n\n---\n\n"
BATCH = 16


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-db", required=True)
    ap.add_argument("--src-collection", required=True)
    ap.add_argument("--dst-db", required=True)
    ap.add_argument("--dst-collection", required=True)
    ap.add_argument("--contexts-jsonl", required=True)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    print(f"[partial] loading contexts from {args.contexts_jsonl}", flush=True)
    contexts: dict[str, str] = {}
    with open(args.contexts_jsonl) as h:
        for line in h:
            row = json.loads(line)
            cid = row["chunk_id"]
            ctx = row["context"].strip()
            if ctx:
                contexts[cid] = ctx
    print(f"[partial] loaded {len(contexts)} contexts", flush=True)

    src_client = chromadb.PersistentClient(path=args.src_db)
    src_col = src_client.get_collection(args.src_collection)
    print(f"[src] reading {src_col.count()} chunks from {args.src_db}:{args.src_collection}", flush=True)
    src_data = src_col.get(include=["documents", "metadatas", "embeddings"])
    ids = src_data["ids"]
    docs = src_data["documents"]
    metas = src_data["metadatas"]
    embs = src_data["embeddings"]
    print(f"[src] loaded {len(ids)} chunks", flush=True)

    dst_client = chromadb.PersistentClient(path=args.dst_db)
    if args.reset:
        try:
            dst_client.delete_collection(args.dst_collection)
            print(f"[dst] dropped {args.dst_collection}", flush=True)
        except Exception:
            pass
    dst_col = dst_client.get_or_create_collection(args.dst_collection, metadata={"hnsw:space": "cosine"})

    pending_ctx_ids: list[int] = []
    pending_ctx_texts: list[str] = []
    keep_ids: list[int] = []

    for i, cid in enumerate(ids):
        if cid in contexts:
            pending_ctx_ids.append(i)
            pending_ctx_texts.append(f"{contexts[cid]}{SEPARATOR}{docs[i]}")
        else:
            keep_ids.append(i)

    print(f"[plan] {len(pending_ctx_ids)} chunks to re-embed (contextualized), {len(keep_ids)} to keep as-is", flush=True)

    # Re-embed contextualized
    new_embs: dict[int, list[float]] = {}
    for batch_start in tqdm(range(0, len(pending_ctx_ids), BATCH), desc="re-embed ctx"):
        batch_idxs = pending_ctx_ids[batch_start : batch_start + BATCH]
        batch_texts = pending_ctx_texts[batch_start : batch_start + BATCH]
        try:
            vecs = embed_texts(batch_texts, is_query=False)
        except Exception as e:
            print(f"\n[batch-fallback] {e}", flush=True)
            vecs = []
            for t in batch_texts:
                try:
                    vecs.append(embed_texts([t], is_query=False)[0])
                except Exception as e2:
                    print(f"\n[skip] {e2}", flush=True)
                    vecs.append(None)
        for src_idx, v in zip(batch_idxs, vecs):
            if v is not None:
                new_embs[src_idx] = v

    print(f"[embed] {len(new_embs)} new embeddings produced", flush=True)

    # Write all chunks: contextualized embeddings where available, original where not
    add_ids = []
    add_embs = []
    add_docs = []
    add_metas = []
    for i, cid in enumerate(ids):
        meta = dict(metas[i])
        if i in new_embs:
            add_ids.append(cid)
            add_embs.append(new_embs[i])
            # Store the CONTEXTUALIZED text in documents so BM25 sees the context tokens too
            add_docs.append(f"{contexts[cid]}{SEPARATOR}{docs[i]}")
            meta["context_applied"] = True
        else:
            add_ids.append(cid)
            add_embs.append(list(embs[i]))
            add_docs.append(docs[i])
            meta["context_applied"] = False
        add_metas.append(meta)

    # Chroma add in chunks to avoid huge single calls
    CHROMA_BATCH = 500
    for s in tqdm(range(0, len(add_ids), CHROMA_BATCH), desc="chroma add"):
        e = s + CHROMA_BATCH
        dst_col.add(
            ids=add_ids[s:e],
            embeddings=add_embs[s:e],
            documents=add_docs[s:e],
            metadatas=add_metas[s:e],
        )

    print(f"[dst] wrote {dst_col.count()} chunks", flush=True)

    # Build BM25 over the partial-context corpus
    import bm25s

    all_data = dst_col.get(include=["documents", "metadatas"])
    print(f"[bm25] tokenizing {len(all_data['documents'])} docs...", flush=True)
    tokenized = [tokenize(d) for d in all_data["documents"]]
    bm25 = bm25s.BM25()
    bm25.index(tokenized)
    bm25.save(Path(args.dst_db) / "bm25s_index")
    with open(Path(args.dst_db) / "bm25_meta.pkl", "wb") as h:
        pickle.dump(
            {"ids": all_data["ids"], "docs": all_data["documents"], "metas": all_data["metadatas"]},
            h,
        )

    print(f"[done] {args.dst_db}:{args.dst_collection} size={dst_col.count()} bm25_saved", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
