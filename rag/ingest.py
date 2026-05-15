"""Ingest markdown corpus into Chroma with nomic-embed-text embeddings."""
import argparse
import pickle
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import chromadb
import ollama
from tqdm import tqdm
from chunker import chunk_markdown, iter_markdown_files
from mitre_loader import iter_mitre_markdown

# Kept identical to retrieve.py::tokenize so the tokenized BM25 corpus persisted
# here is usable as-is in retrieval. Change both places together if ever altered.
TOKEN_RE = re.compile(r"\w+")

def tokenize(text: str):
    return [t.lower() for t in TOKEN_RE.findall(text)]

EMBED_MODEL = "nomic-embed-text"
DEFAULT_DB = "chroma_db"
COLLECTION = "security"
BATCH = 64
MAX_CHARS_FOR_EMBED = 1500  # ~375 tokens, safe even for CJK/code-dense content
EMBED_NUM_CTX = 8192  # nomic-embed-text native max (Ollama default is only 2048)

SOURCES = {
    "hacktricks": "corpus/hacktricks",
    "payloads": "corpus/PayloadsAllTheThings",
    "owasp": "corpus/CheatSheetSeries",
    "mitre": "corpus/cti",
}

def _embed_one_with_fallback(text: str):
    """Per-chunk embed with harsher truncation retry. Used when a batched call fails
    so a single bad chunk doesn't kill the whole batch."""
    safe = text[:MAX_CHARS_FOR_EMBED]
    try:
        r = ollama.embed(model=EMBED_MODEL, input=safe, options={"num_ctx": EMBED_NUM_CTX})
        return r["embeddings"][0]
    except Exception:
        try:
            r = ollama.embed(model=EMBED_MODEL, input=text[:600], options={"num_ctx": EMBED_NUM_CTX})
            return r["embeddings"][0]
        except Exception as e2:
            print(f"\n[skip] embed failed: {e2}", flush=True)
            return None


def embed_batch(texts):
    """One batched Ollama call per BATCH; on failure, fall back to per-chunk retries.
    Returns (vectors, keep_mask) — keep_mask[i] is False if chunk i was dropped."""
    safe_texts = [t[:MAX_CHARS_FOR_EMBED] for t in texts]
    try:
        r = ollama.embed(model=EMBED_MODEL, input=safe_texts, options={"num_ctx": EMBED_NUM_CTX})
        vecs = r["embeddings"]
        if len(vecs) == len(texts):
            return vecs, [True] * len(texts)
    except Exception as e:
        print(f"\n[batch-fallback] {e}", flush=True)
    # Fallback: one chunk at a time so one overflow doesn't nuke 63 good chunks.
    vecs, keep = [], []
    for t in texts:
        v = _embed_one_with_fallback(t)
        if v is None:
            vecs.append(None)
            keep.append(False)
        else:
            vecs.append(v)
            keep.append(True)
    return vecs, keep

def _read_md(task):
    root, md_path = task
    try:
        rp = str(md_path.relative_to(root))
        md = md_path.read_text(encoding="utf-8", errors="ignore")
        return rp, md
    except Exception:
        return None


def collect_chunks(sources):
    chunks = []
    for name, rel in sources.items():
        root = Path(rel)
        if not root.exists():
            print(f"[skip] {name}: {root} not found")
            continue
        n_before = len(chunks)
        if name == "mitre":
            for rel_path, md in iter_mitre_markdown(root):
                chunks.extend(chunk_markdown(md, name, rel_path))
        else:
            tasks = [(root, p) for p in iter_markdown_files(root)]
            # Reads release the GIL, so threads overlap I/O across files.
            # Chunking runs serially on main thread (CPU-bound, GIL-bound regex).
            with ThreadPoolExecutor(max_workers=8) as ex:
                for result in ex.map(_read_md, tasks, chunksize=16):
                    if result is None:
                        continue
                    rp, md = result
                    chunks.extend(chunk_markdown(md, name, rp))
        print(f"[{name}] {len(chunks) - n_before} chunks")
    return chunks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", nargs="*", default=list(SOURCES.keys()))
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    selected = {k: SOURCES[k] for k in args.sources if k in SOURCES}
    chunks = collect_chunks(selected)
    print(f"Total chunks: {len(chunks)}")
    if not chunks:
        return

    client = chromadb.PersistentClient(path=args.db)
    if args.reset:
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    existing = set(col.get(include=[])["ids"]) if col.count() else set()
    new_chunks = [c for c in chunks if c.chunk_id not in existing]
    print(f"New chunks to embed: {len(new_chunks)} (skipping {len(chunks) - len(new_chunks)} existing)")

    dropped = 0
    for i in tqdm(range(0, len(new_chunks), BATCH), desc="embed+add"):
        batch = new_chunks[i : i + BATCH]
        vecs, keep = embed_batch([c.text for c in batch])
        kept_batch = [(c, v) for c, v, k in zip(batch, vecs, keep) if k]
        dropped += len(batch) - len(kept_batch)
        if not kept_batch:
            continue
        col.add(
            ids=[c.chunk_id for c, _ in kept_batch],
            embeddings=[v for _, v in kept_batch],
            documents=[c.text for c, _ in kept_batch],
            metadatas=[{"source": c.source, "rel_path": c.rel_path, "section_path": c.section_path} for c, _ in kept_batch],
        )
    if dropped:
        print(f"[warn] skipped {dropped} oversized/failed chunks")

    # Build BM25 corpus snapshot of ALL chunks (new + existing) for hybrid retrieval.
    # Tokenize once here so retrieve.py can skip the ~15s retokenization at startup.
    import bm25s

    all_data = col.get(include=["documents", "metadatas"])
    print("[bm25] tokenizing corpus…", flush=True)
    tokenized = [tokenize(d) for d in all_data["documents"]]
    bm25 = bm25s.BM25()
    bm25.index(tokenized)

    bm25_index_dir = Path(args.db) / "bm25s_index"
    bm25_index_dir.parent.mkdir(exist_ok=True)
    bm25.save(bm25_index_dir)

    bm25_meta = {
        "ids": all_data["ids"],
        "docs": all_data["documents"],
        "metas": all_data["metadatas"],
    }
    with open(Path(args.db) / "bm25_meta.pkl", "wb") as f:
        pickle.dump(bm25_meta, f)
    print(f"Collection size: {col.count()}. BM25 index saved (bm25s).")

if __name__ == "__main__":
    main()
