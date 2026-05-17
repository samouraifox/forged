"""Generate all 2,300 source-document + chunk-list work items for the
Phase 3c.1 main run. Run once before dispatching subagent batches."""

import json
import re
from collections import defaultdict
from pathlib import Path

import chromadb

SUFFIX_RE = re.compile(r".*::(\d+)$")


def main() -> None:
    c = chromadb.PersistentClient(path="rag/chroma_db_qwen3")
    col = c.get_collection("forged_v2_qwen3_emb")
    data = col.get(include=["documents", "metadatas"])

    groups = defaultdict(list)
    for cid, doc, meta in zip(data["ids"], data["documents"], data["metadatas"]):
        key = (meta.get("source", "?"), meta.get("rel_path", "?"))
        groups[key].append({"id": cid, "doc": doc, "meta": meta})

    def chunk_pos(cid: str) -> int:
        m = SUFFIX_RE.match(cid)
        return int(m.group(1)) if m else 10**9

    for k in groups:
        groups[k].sort(key=lambda x: (chunk_pos(x["id"]), x["id"]))

    main_work = Path("rag/contextualize/main")
    main_work.mkdir(parents=True, exist_ok=True)

    items = sorted(groups.items(), key=lambda x: (x[0][0], x[0][1]))
    manifest = []
    for idx, (key, chunks) in enumerate(items):
        source, rel_path = key
        src_text = "\n\n".join(c["doc"] for c in chunks)
        chunk_list = [{"chunk_id": c["id"], "text": c["doc"]} for c in chunks]
        (main_work / f"source_{idx:04d}.md").write_text(src_text, encoding="utf-8")
        (main_work / f"source_{idx:04d}_chunks.json").write_text(
            json.dumps(chunk_list, indent=1), encoding="utf-8"
        )
        manifest.append(
            {
                "idx": idx,
                "source": source,
                "rel_path": rel_path,
                "chunk_count": len(chunks),
                "src_chars": len(src_text),
            }
        )

    (main_work / "manifest.json").write_text(json.dumps(manifest, indent=1))

    total_chunks = sum(m["chunk_count"] for m in manifest)
    print(f"wrote {len(manifest)} sources into {main_work}/")
    print(f"total chunks: {total_chunks}")
    big = sorted(manifest, key=lambda m: -m["chunk_count"])[:10]
    print("top 10 by chunks:")
    for m in big:
        print(
            f"  idx={m['idx']:04d} "
            f"{m['source']}/{m['rel_path'][:55]} "
            f"chunks={m['chunk_count']} chars={m['src_chars']}"
        )

    # Distribution buckets
    buckets = defaultdict(int)
    for m in manifest:
        n = m["chunk_count"]
        if n == 1:
            buckets["1"] += 1
        elif n <= 5:
            buckets["2-5"] += 1
        elif n <= 20:
            buckets["6-20"] += 1
        elif n <= 50:
            buckets["21-50"] += 1
        else:
            buckets["51+"] += 1
    print(f"size distribution: {dict(buckets)}")


if __name__ == "__main__":
    main()
