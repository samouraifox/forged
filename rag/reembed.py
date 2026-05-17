"""Re-embed an existing Chroma collection's documents under a new embedder.

Phase 3a uses this instead of `ingest.py` because the source markdown corpus
(corpus/hacktricks, corpus/PayloadsAllTheThings, corpus/CheatSheetSeries,
corpus/cti) is gitignored and was not preserved alongside the existing
chroma_db. The original 14,308 chunks live inside the existing collection
with their text in the `documents` field, so we read from there directly.

Side-benefit over re-ingesting: the chunk boundaries, IDs, and text are
byte-identical, which gives a strictly clean A/B (only the vector changes).
A fresh ingest could pick up upstream corpus updates (HackTricks edits its
content frequently) and confound the embedder comparison.

Writes a new chroma DB + collection + BM25 snapshot into a separate
directory so the v1 stack remains intact and reversible.
"""

from __future__ import annotations

import argparse
import pickle
import re
from pathlib import Path

import chromadb
from tqdm import tqdm

from embedder import embed_texts, active_backend

TOKEN_RE = re.compile(r"\w+")
# Batch size tuned for Intel Arc 140V iGPU memory budget. The iGPU shares
# system RAM; OpenVINO's GPU plugin allocates activation buffers per call.
# At BATCH=64 + L=900 tokens the OpenCL driver hits CL_OUT_OF_RESOURCES.
# BATCH=16 keeps the per-batch activation footprint under control while
# still amortizing tokenization + OpenVINO submit overhead.
BATCH = 16


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-db", required=True, help="Source Chroma DB directory")
    ap.add_argument("--src-collection", required=True, help="Source collection name")
    ap.add_argument("--dst-db", required=True, help="Target Chroma DB directory (will be created)")
    ap.add_argument("--dst-collection", required=True, help="Target collection name")
    ap.add_argument("--reset", action="store_true", help="Drop target collection before writing")
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only re-embed the first N chunks (smoke testing).",
    )
    args = ap.parse_args()

    print(f"[reembed] embedder: {active_backend()}", flush=True)

    src_client = chromadb.PersistentClient(path=args.src_db)
    src_col = src_client.get_collection(args.src_collection)
    src_count = src_col.count()
    print(f"[src] {args.src_db} :: {args.src_collection} has {src_count} chunks", flush=True)

    src_data = src_col.get(include=["documents", "metadatas"])
    ids = src_data["ids"]
    docs = src_data["documents"]
    metas = src_data["metadatas"]
    if args.limit is not None:
        ids = ids[: args.limit]
        docs = docs[: args.limit]
        metas = metas[: args.limit]
    print(f"[src] read {len(ids)} chunks for re-embedding", flush=True)

    dst_client = chromadb.PersistentClient(path=args.dst_db)
    if args.reset:
        try:
            dst_client.delete_collection(args.dst_collection)
            print(f"[dst] dropped existing collection {args.dst_collection}", flush=True)
        except Exception:
            pass
    dst_col = dst_client.get_or_create_collection(
        args.dst_collection,
        metadata={"hnsw:space": "cosine"},
    )

    existing_dst = set(dst_col.get(include=[])["ids"]) if dst_col.count() else set()
    pending_indices = [i for i, cid in enumerate(ids) if cid not in existing_dst]
    print(
        f"[dst] {args.dst_db} :: {args.dst_collection} has {len(existing_dst)} chunks; "
        f"{len(pending_indices)} pending",
        flush=True,
    )

    dropped = 0
    for batch_start in tqdm(range(0, len(pending_indices), BATCH), desc="reembed+add"):
        batch_idxs = pending_indices[batch_start : batch_start + BATCH]
        batch_texts = [docs[i] for i in batch_idxs]
        try:
            vecs = embed_texts(batch_texts, is_query=False)
        except Exception as e:
            print(f"\n[batch-fallback] {e}", flush=True)
            vecs = []
            for t in batch_texts:
                try:
                    vecs.append(embed_texts([t], is_query=False)[0])
                except Exception as e2:
                    print(f"\n[skip] embed failed: {e2}", flush=True)
                    vecs.append(None)
        kept = [(i, v) for i, v in zip(batch_idxs, vecs) if v is not None]
        dropped += len(batch_idxs) - len(kept)
        if not kept:
            continue
        dst_col.add(
            ids=[ids[i] for i, _ in kept],
            embeddings=[v for _, v in kept],
            documents=[docs[i] for i, _ in kept],
            metadatas=[metas[i] for i, _ in kept],
        )

    if dropped:
        print(f"[warn] skipped {dropped} chunks that failed to embed", flush=True)

    import bm25s

    all_data = dst_col.get(include=["documents", "metadatas"])
    print(f"[bm25] tokenizing {len(all_data['documents'])} docs...", flush=True)
    tokenized = [tokenize(d) for d in all_data["documents"]]
    bm25 = bm25s.BM25()
    bm25.index(tokenized)

    bm25_index_dir = Path(args.dst_db) / "bm25s_index"
    bm25.save(bm25_index_dir)

    bm25_meta = {
        "ids": all_data["ids"],
        "docs": all_data["documents"],
        "metas": all_data["metadatas"],
    }
    with open(Path(args.dst_db) / "bm25_meta.pkl", "wb") as handle:
        pickle.dump(bm25_meta, handle)

    print(
        f"[done] {args.dst_db} :: {args.dst_collection} collection_size={dst_col.count()} "
        f"bm25_saved",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
