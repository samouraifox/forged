"""Enrich the 9-cve-deep-dive.md with the actual chunk text snippets,
the gold substring list from questions.jsonl, and gold path patterns —
so the cybersec engineer doesn't have to grep the corpus to read it."""

import json
from pathlib import Path

import chromadb

REPO = Path(__file__).resolve().parent.parent.parent
RESULTS = REPO / "eval" / "results"
BUNDLE = REPO / "eval" / "review-bundles" / "2026-05-17-day3-engineer-review"
QUESTIONS = REPO / "eval" / "questions.jsonl"

V3A = RESULTS / "2026-05-17_v2-day3a-qwen3emb-fixed-retrieval.json"
V3B = RESULTS / "2026-05-17_v2-day3b-qwen3rerank-retrieval.json"
V3C = RESULTS / "2026-05-17_v2-day3c-partial-ctx-1421-retrieval.json"


def load_questions() -> dict:
    out = {}
    with open(QUESTIONS) as h:
        for line in h:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            out[q["id"]] = q
    return out


def fetch_chunk_texts(chunk_ids: list[str]) -> dict[str, dict]:
    """Pull `{id: {text, meta}}` straight from the partial-context Chroma
    collection (which stores the contextualized text where applicable)
    and the base 3a/3b collection (raw chunk text). We need both so
    we can show both views."""
    out_raw: dict[str, dict] = {}
    out_ctx: dict[str, dict] = {}
    c_raw = chromadb.PersistentClient(path=str(REPO / "rag" / "chroma_db_qwen3"))
    col_raw = c_raw.get_collection("forged_v2_qwen3_emb")
    data_raw = col_raw.get(ids=chunk_ids, include=["documents", "metadatas"])
    for cid, doc, meta in zip(data_raw["ids"], data_raw["documents"], data_raw["metadatas"]):
        out_raw[cid] = {"text": doc, "meta": meta}

    c_ctx = chromadb.PersistentClient(path=str(REPO / "rag" / "chroma_db_qwen3_partial_ctx"))
    col_ctx = c_ctx.get_collection("forged_v2_qwen3_emb_context_partial_1421")
    data_ctx = col_ctx.get(ids=chunk_ids, include=["documents", "metadatas"])
    for cid, doc, meta in zip(data_ctx["ids"], data_ctx["documents"], data_ctx["metadatas"]):
        out_ctx[cid] = {"text": doc, "meta": meta}
    return {"raw": out_raw, "ctx": out_ctx}


def fmt_snippet(text: str, length: int = 400) -> str:
    """Snip + escape pipes for markdown table tolerance."""
    s = text.strip()[:length]
    if len(text) > length:
        s += "…"
    return s


def topk_table(hits: list[dict], texts_raw: dict, texts_ctx: dict, header: str) -> str:
    lines = []
    lines.append(f"**{header}**")
    lines.append("")
    for i, hit in enumerate(hits, 1):
        cid = hit.get("id", "?")
        rerank = hit.get("rerank")
        rerank_s = f"rerank={rerank:.4f}" if rerank is not None else "rerank=—"
        rrf = hit.get("rrf")
        rrf_s = f"rrf={rrf:.4f}" if rrf is not None else "rrf=—"
        dr = hit.get("dense_rank")
        sr = hit.get("sparse_rank")
        rank_str = f"dense_rank={dr}" if dr is not None else "dense_rank=—"
        rank_str += f", sparse_rank={sr}" if sr is not None else ", sparse_rank=—"
        source = hit.get("source", "?")
        rp = hit.get("rel_path", "?")
        sp = hit.get("section_path") or ""
        lines.append(f"<details><summary><b>#{i} — {source}/{rp}</b> · section: <code>{sp}</code> · {rerank_s} · {rrf_s} · {rank_str}</summary>")
        lines.append("")
        ctx_meta = texts_ctx.get(cid, {}).get("meta") or {}
        ctx_applied = ctx_meta.get("context_applied", False)
        if ctx_applied:
            lines.append("**context_applied = true** (this chunk has a generated context prepended in the partial-3c collection)")
            lines.append("")
            lines.append("**Contextualized text (what 3c partial embedding + BM25 see):**")
            lines.append("```")
            lines.append(fmt_snippet(texts_ctx.get(cid, {}).get("text", "(missing)")))
            lines.append("```")
            lines.append("")
            lines.append("**Original chunk text (what 3a and 3b embedding + BM25 see):**")
        else:
            lines.append("**context_applied = false** (chunk unchanged across all three stages)")
            lines.append("")
            lines.append("**Chunk text (identical at all three stages):**")
        lines.append("```")
        lines.append(fmt_snippet(texts_raw.get(cid, {}).get("text", "(missing)")))
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    return "\n".join(lines)


def main():
    questions = load_questions()
    v3a = json.loads(V3A.read_text())
    v3b = json.loads(V3B.read_text())
    v3c = json.loads(V3C.read_text())

    a_by = {r["id"]: r for r in v3a["per_question"]}
    b_by = {r["id"]: r for r in v3b["per_question"]}
    c_by = {r["id"]: r for r in v3c["per_question"]}

    cve_ids = [
        qid for qid, r in a_by.items()
        if r["category"] == "cve-specific" and r["score"]["path_recall"] == 0.0
    ]
    cve_ids.sort()

    # collect all unique chunk_ids across the 9 questions × 3 stages
    chunk_id_set = set()
    for qid in cve_ids:
        for stage in (a_by, b_by, c_by):
            for hit in stage[qid]["retrieved_chunks"]:
                chunk_id_set.add(hit["id"])
    print(f"Fetching {len(chunk_id_set)} unique chunk texts...", flush=True)
    fetched = fetch_chunk_texts(list(chunk_id_set))
    texts_raw = fetched["raw"]
    texts_ctx = fetched["ctx"]

    out = []
    out.append("# 9 CVE Deep Dive — top-5 retrieved chunks at each retrieval-stack stage")
    out.append("")
    out.append("All 9 questions have `path_recall=0` at every retrieval stage from v1 through 3c partial.")
    out.append("This document shows the **actual chunk text** of what the retriever surfaced at")
    out.append("each stage, so the engineer can read whether (a) the right content is being retrieved")
    out.append("but at a wrong-but-related path (rubric path-recall is too strict), or (b) the right")
    out.append("content is genuinely absent from the corpus and the corpus-pipeline memo is the trigger.")
    out.append("")
    out.append("Stack legend:")
    out.append("- **3a** = Qwen3-Embedding + MiniLM CrossEncoder reranker")
    out.append("- **3b** = Qwen3-Embedding + Qwen3-Reranker")
    out.append("- **3c partial** = Qwen3-Embedding (1,421 contextualized chunks) + Qwen3-Reranker; the partial-context Chroma collection prepends a 50-100 token context to chunks where one was generated")
    out.append("")
    out.append("For each retrieved chunk, the markdown shows: source · rel_path · section_path · rerank/rrf/dense/sparse scores. Click the chunk header to expand and read the actual chunk text (and the contextualized version, where the context was generated).")
    out.append("")
    out.append("---")
    out.append("")
    for qid in cve_ids:
        q_meta = questions.get(qid, {})
        out.append(f"## {qid}")
        out.append("")
        out.append(f"**Question**: {q_meta.get('question', a_by[qid]['question'])}")
        out.append("")
        out.append(f"**Category**: {q_meta.get('category','?')}")
        out.append("")
        # gold-label transparency: dump from questions.jsonl
        gold_paths = q_meta.get("gold_chunk_paths") or []
        gold_subs = q_meta.get("gold_chunk_substrings") or []
        must = q_meta.get("must_mention_facts") or []
        not_h = q_meta.get("must_not_hallucinate") or []
        out.append(f"**Gold chunk path fragments** (what `path_recall` looks for in `rel_path`):")
        out.append("")
        if gold_paths:
            for g in gold_paths:
                out.append(f"- `{g}`")
        else:
            out.append("- (none — `path_recall` is vacuous-1.0 only when this list is empty; here it's the scored case)")
        out.append("")
        out.append(f"**Gold chunk substrings** (what `substring_recall` looks for in chunk text / paths):")
        out.append("")
        if gold_subs:
            for g in gold_subs:
                out.append(f"- `{g}`")
        else:
            out.append("- (none)")
        out.append("")
        out.append(f"**Must-mention facts** (rubric, not retrieval-side):")
        out.append("")
        for f in must:
            if isinstance(f, list):
                out.append(f"- any-of: {', '.join('`'+s+'`' for s in f)}")
            else:
                out.append(f"- `{f}`")
        out.append("")
        out.append(f"**Retrieval scores by stage**:")
        out.append("")
        out.append("| stage | retrieval_score | path_recall | substring_recall |")
        out.append("|---|---|---|---|")
        for stage_label, stage_doc in (("3a", a_by), ("3b", b_by), ("3c partial", c_by)):
            sc = stage_doc[qid]["score"]
            out.append(f"| {stage_label} | {sc['retrieval_score']:.3f} | {sc['path_recall']:.3f} | {sc['substring_recall']:.3f} |")
        out.append("")
        out.append(topk_table(a_by[qid]["retrieved_chunks"], texts_raw, texts_ctx, "3a top-5"))
        out.append(topk_table(b_by[qid]["retrieved_chunks"], texts_raw, texts_ctx, "3b top-5"))
        out.append(topk_table(c_by[qid]["retrieved_chunks"], texts_raw, texts_ctx, "3c partial top-5 (final stack)"))
        out.append("---")
        out.append("")

    out_path = BUNDLE / "9-cve-deep-dive.md"
    out_path.write_text("\n".join(out))
    print(f"Wrote {out_path}  ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
