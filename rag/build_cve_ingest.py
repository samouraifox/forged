"""Build the CVE-full Chroma collection for Phase 3.5 ingestion.

For each CVE folder under data/cve_ingest/, chunk every *.md, embed raw text
with Qwen3-Embedding (no Sonnet-context wrapping — corpus-pipeline is parked),
and append into a new combined collection seeded from the partial-3c baseline.

Per-chunk metadata:
  source_type    nvd | mitre | blog | exploit_db   (derived from filename stem)
  primary_cve    canonical CVE id of the source file's CVE
  is_sibling_of  CVE id of the eval-tracked primary it siblings (None for primaries)
  source_url     parsed from the '**Source URL:** {url}' line in the markdown
  rel_path       {folder}/{filename-stem}    (folder name uses semantic keyword)

Smoke set (Phase 3.5 step 1):
  spring-cloud-spel/ → CVE-2022-22963 (sibling of CVE-2022-22965 Spring4Shell)
  dirtypipe/         → CVE-2022-0847  (sibling of CVE-2021-4034 PwnKit)

Adding the full inventory: expand FOLDER_META with primary CVEs (is_sibling_of=None)
and remaining siblings. Source files must already exist; this script never writes
.md files itself.

Inputs:
  data/cve_ingest/{folder}/*.md
  rag/chroma_db_qwen3_partial_ctx/forged_v2_qwen3_emb_context_partial_1421  (read-only)

Output:
  rag/chroma_db_cve_full/forged_v2_qwen3_emb_cve_full   (Chroma + BM25)
"""

from __future__ import annotations

import argparse
import pickle
import re
import sys
from pathlib import Path

import chromadb
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chunker import chunk_markdown  # noqa: E402
from embedder import embed_texts  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DATA_ROOT = REPO / "data" / "cve_ingest"
BASELINE_DB = REPO / "rag" / "chroma_db_qwen3_partial_ctx"
BASELINE_COLLECTION = "forged_v2_qwen3_emb_context_partial_1421"
DST_DB = REPO / "rag" / "chroma_db_cve_full"
DST_COLLECTION = "forged_v2_qwen3_emb_cve_full"
BATCH = 16
CHROMA_BATCH = 500
TOKEN_RE = re.compile(r"\w+")
SOURCE_URL_RE = re.compile(r"^\*\*Source URL:\*\*\s*(\S+)", re.MULTILINE)

# folder (semantic keyword) → (primary_cve, is_sibling_of)
# is_sibling_of = None for eval-tracked primary CVEs; a CVE id for siblings.
# For the ProxyShell chain, primary_cve is the +-joined triplet (chain entry
# is CVE-2021-34473 backend SSRF; chained with -34523 path confusion and
# -31207 PUT-to-shell). Other chained CVEs may follow the same convention.
FOLDER_META: dict[str, tuple[str, str | None]] = {
    # ─── Primaries (9 eval-tracked, q-001/003/004/005/006/007/008/009/010) ───
    # Three folder names carry compound keywords so the rubric's
    # gold_chunk_paths can match every required keyword as a substring:
    #   sudo-baron-samedit/    carries "sudo" (q-004 gold) and the
    #                          disambiguating CVE id slug
    #   proxyshell-exchange/   carries "proxyshell" and "exchange"
    #                          (q-005 gold is both)
    #   citrixbleed-netscaler/ carries "citrixbleed" and "netscaler"
    #                          (q-006 gold is both)
    "spring4shell":             ("CVE-2022-22965", None),
    "pwnkit":                   ("CVE-2021-4034",  None),
    "sudo-baron-samedit":       ("CVE-2021-3156",  None),
    "proxyshell-exchange":      ("CVE-2021-34473+CVE-2021-34523+CVE-2021-31207", None),
    "citrixbleed-netscaler":    ("CVE-2023-4966",  None),
    "moveit":                   ("CVE-2023-34362", None),
    "confluence":               ("CVE-2022-26134", None),
    "polkit-dbus":              ("CVE-2021-3560",  None),
    "goanywhere-mft":           ("CVE-2023-0669",  None),
    # ─── Siblings (17 bounded — DO NOT add others) ───
    # Spring4Shell family
    "spring-cloud-spel":  ("CVE-2022-22963", "CVE-2022-22965"),   # smoke
    "spring-data-rest":   ("CVE-2017-8046",  "CVE-2022-22965"),
    # PwnKit family
    "samba-rce":          ("CVE-2017-7494",  "CVE-2021-4034"),
    "dirtypipe":          ("CVE-2022-0847",  "CVE-2021-4034"),    # smoke (also sib of polkit-dbus)
    # Baron Samedit family
    "sudo-pwfeedback":    ("CVE-2019-18634", "CVE-2021-3156"),
    "sudoedit":           ("CVE-2023-22809", "CVE-2021-3156"),
    # ProxyShell family
    "proxylogon":         ("CVE-2021-26855", "CVE-2021-34473"),
    "proxynotshell":      ("CVE-2022-41040", "CVE-2021-34473"),
    # CitrixBleed family
    "citrix-dirtraversal":   ("CVE-2019-19781", "CVE-2023-4966"),
    "netscaler-authbypass":  ("CVE-2022-27510", "CVE-2023-4966"),
    # MOVEit family
    "moveit-authbypass-2024": ("CVE-2024-5806",  "CVE-2023-34362"),
    "moveit-2023-followup":   ("CVE-2023-35036", "CVE-2023-34362"),
    # Confluence OGNL family
    "confluence-privesc":     ("CVE-2023-22515", "CVE-2022-26134"),
    "vmware-workspace-ognl":  ("CVE-2022-22954", "CVE-2022-26134"),
    # polkit family
    "kernel-netfilter-privesc": ("CVE-2016-3134", "CVE-2021-3560"),
    # GoAnywhere family
    "fortra-goanywhere-2024":      ("CVE-2024-0204",  "CVE-2023-0669"),
    "adobe-coldfusion-filetransfer": ("CVE-2023-29298", "CVE-2023-0669"),
}


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def derive_source_type(filename_stem: str) -> str:
    """Map filename stem to source_type. Prefix-aware so chains (e.g.
    proxyshell/nvd_34473) and richer naming (vendor_advisory_atlassian) work."""
    s = filename_stem.lower()
    if s == "nvd" or s.startswith("nvd_"):
        return "nvd"
    if s == "vendor_advisory" or s.startswith("vendor_advisory_"):
        return "vendor_advisory"
    if s == "exploit_db" or s.startswith("exploit_db_") or s == "exploitdb":
        return "exploit_db"
    if s == "blog" or s.startswith("blog_") or s.startswith("blog-"):
        return "blog"
    raise RuntimeError(
        f"unrecognized filename stem {filename_stem!r}: expected "
        "nvd[_*] / vendor_advisory[_*] / exploit_db[_*] / blog[_*]"
    )


def parse_source_url(md_text: str, file_path: Path) -> str:
    m = SOURCE_URL_RE.search(md_text)
    if not m:
        raise RuntimeError(
            f"{file_path} missing '**Source URL:** {{url}}' line — required for source_url metadata"
        )
    return m.group(1).strip()


def collect_chunks() -> list[dict]:
    rows: list[dict] = []
    for folder_name, (primary_cve, sibling_of) in sorted(FOLDER_META.items()):
        folder = DATA_ROOT / folder_name
        if not folder.is_dir():
            print(f"[skip] missing folder {folder} (primary_cve={primary_cve}) — "
                  "source-fetcher failed for this CVE; continuing",
                  flush=True)
            continue
        md_files = sorted(folder.glob("*.md"))
        if not md_files:
            print(f"[skip] empty folder {folder} (primary_cve={primary_cve}) — "
                  "no sources fetched; continuing",
                  flush=True)
            continue
        for md_path in md_files:
            md_text = md_path.read_text(encoding="utf-8")
            source_url = parse_source_url(md_text, md_path)
            source_type = derive_source_type(md_path.stem)
            rel_path = f"{folder_name}/{md_path.stem}"
            for ch in chunk_markdown(md_text, "cve_ingest", rel_path):
                rows.append({
                    "chunk_id": f"cve_ingest::{rel_path}::{len(rows)}",
                    "text": ch.text,
                    "source": ch.source,
                    "rel_path": ch.rel_path,
                    "section_path": ch.section_path,
                    "source_type": source_type,
                    "primary_cve": primary_cve,
                    "is_sibling_of": sibling_of if sibling_of is not None else "",
                    "source_url": source_url,
                })
    return rows


def batched(iterable, n):
    buf = []
    for x in iterable:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf


def embed_chunks(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for batch in tqdm(list(batched(texts, BATCH)), desc="embed"):
        vecs = embed_texts(batch, is_query=False)
        out.extend(vecs)
    return out


def build_collection(rows: list[dict]) -> None:
    if DST_DB.exists():
        import shutil
        shutil.rmtree(DST_DB)
    DST_DB.mkdir(parents=True)

    src_client = chromadb.PersistentClient(path=str(BASELINE_DB))
    src_col = src_client.get_collection(BASELINE_COLLECTION)
    src = src_col.get(include=["documents", "metadatas", "embeddings"])
    print(f"[baseline] {len(src['ids'])} chunks", flush=True)

    dst_client = chromadb.PersistentClient(path=str(DST_DB))
    dst_col = dst_client.get_or_create_collection(
        DST_COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    for s in tqdm(range(0, len(src["ids"]), CHROMA_BATCH), desc="copy baseline"):
        e = s + CHROMA_BATCH
        dst_col.add(
            ids=src["ids"][s:e],
            embeddings=[list(v) for v in src["embeddings"][s:e]],
            documents=src["documents"][s:e],
            metadatas=src["metadatas"][s:e],
        )

    texts = [r["text"] for r in rows]
    print(f"[ingest] embedding {len(texts)} CVE chunks across "
          f"{len(set(r['primary_cve'] for r in rows))} CVEs...", flush=True)
    embs = embed_chunks(texts)

    add_ids = [r["chunk_id"] for r in rows]
    add_metas = [
        {
            "source": r["source"],
            "rel_path": r["rel_path"],
            "section_path": r["section_path"],
            "source_type": r["source_type"],
            "primary_cve": r["primary_cve"],
            "is_sibling_of": r["is_sibling_of"],
            "source_url": r["source_url"],
        }
        for r in rows
    ]
    for s in range(0, len(add_ids), CHROMA_BATCH):
        e = s + CHROMA_BATCH
        dst_col.add(
            ids=add_ids[s:e],
            embeddings=embs[s:e],
            documents=texts[s:e],
            metadatas=add_metas[s:e],
        )
    print(f"[ingest] dst total = {dst_col.count()} chunks", flush=True)

    import bm25s

    all_data = dst_col.get(include=["documents", "metadatas"])
    print(f"[bm25] tokenizing {len(all_data['documents'])} docs...", flush=True)
    tokenized = [tokenize(d) for d in all_data["documents"]]
    bm25 = bm25s.BM25()
    bm25.index(tokenized)
    bm25.save(DST_DB / "bm25s_index")
    with open(DST_DB / "bm25_meta.pkl", "wb") as h:
        pickle.dump(
            {"ids": all_data["ids"], "docs": all_data["documents"], "metas": all_data["metadatas"]},
            h,
        )
    print(f"[bm25] saved to {DST_DB / 'bm25s_index'}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Collect+report chunk plan without building the collection.")
    args = ap.parse_args()

    print(f"[plan] reading sources from {DATA_ROOT}", flush=True)
    rows = collect_chunks()
    print(f"[plan] {len(rows)} chunks across {len(FOLDER_META)} CVE folders", flush=True)
    for folder_name, (primary_cve, sibling_of) in sorted(FOLDER_META.items()):
        n = sum(1 for r in rows if r["rel_path"].startswith(f"{folder_name}/"))
        sib = f" (sibling of {sibling_of})" if sibling_of else " (primary)"
        print(f"  {folder_name}: {n} chunks → {primary_cve}{sib}", flush=True)

    if args.dry_run:
        print("[dry-run] skipping build.", flush=True)
        return 0

    build_collection(rows)
    print("[done]", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
