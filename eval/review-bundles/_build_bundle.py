"""Generate the Day 3 engineer-review bundle markdown artifacts.

Reads the three Phase 3 result JSONs and writes:
- README.md with aggregate + per-category + per-question movement tables
- 9-cve-deep-dive.md with top-5 retrieved chunks at each retrieval-stack stage
- Copies the three result JSONs alongside.
"""

import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
RESULTS = REPO / "eval" / "results"
BUNDLE = REPO / "eval" / "review-bundles" / "2026-05-17-day3-engineer-review"

V3A = RESULTS / "2026-05-17_v2-day3a-qwen3emb-fixed-retrieval.json"
V3B = RESULTS / "2026-05-17_v2-day3b-qwen3rerank-retrieval.json"
V3C = RESULTS / "2026-05-17_v2-day3c-partial-ctx-1421-retrieval.json"

# Locked v1 + v2-Day2 rubric-patched aggregates for comparison context
V1_RUBRIC = RESULTS / "2026-05-16_v1-baseline-50q-final_rubric-patched.json"
V2D2_RUBRIC = RESULTS / "2026-05-16_v2-day2-hermes4_rubric-patched.json"


def fmt(v, w=10, p=3):
    if v is None:
        return f"{'n/a':>{w}}"
    return f"{v:>{w}.{p}f}"


def diff_table_aggregate(stages: list[tuple[str, dict]]) -> str:
    """Build markdown table of mean retrieval across stages."""
    out = []
    headers = ["category"] + [s[0] for s in stages]
    out.append("| " + " | ".join(headers) + " |")
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    cats = sorted(stages[0][1]["aggregate_by_category"].keys())
    for cat in cats:
        row = [cat]
        for _, doc in stages:
            v = doc["aggregate_by_category"][cat]["mean_retrieval_score"]
            row.append(f"{v:.3f}")
        out.append("| " + " | ".join(row) + " |")
    # overall
    row = ["**OVERALL**"]
    for _, doc in stages:
        v = doc["aggregate"]["mean_retrieval_score"]
        row.append(f"**{v:.3f}**")
    out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def per_question_movement(v3a: dict, v3b: dict, v3c: dict) -> str:
    out = []
    out.append("| id | category | 3a | 3b | 3c partial | Δ(3b−3a) | Δ(3c−3b) | Δ(3c−3a) |")
    out.append("|---|---|---|---|---|---|---|---|")
    by_id = {
        "3a": {r["id"]: r for r in v3a["per_question"]},
        "3b": {r["id"]: r for r in v3b["per_question"]},
        "3c": {r["id"]: r for r in v3c["per_question"]},
    }
    for qid in sorted(by_id["3a"]):
        a = by_id["3a"][qid]["score"]["retrieval_score"]
        b = by_id["3b"][qid]["score"]["retrieval_score"]
        c = by_id["3c"][qid]["score"]["retrieval_score"]
        d_ba = b - a
        d_cb = c - b
        d_ca = c - a
        out.append(
            f"| {qid} | {by_id['3a'][qid]['category']} | "
            f"{a:.3f} | {b:.3f} | {c:.3f} | {d_ba:+.3f} | {d_cb:+.3f} | {d_ca:+.3f} |"
        )
    return "\n".join(out)


def per_question_movement_changed_only(v3a: dict, v3b: dict, v3c: dict) -> str:
    """Only show questions whose retrieval_score moved at any stage."""
    out = []
    out.append("| id | category | 3a | 3b | 3c partial | Δ(3b−3a) | Δ(3c−3b) | Δ(3c−3a) |")
    out.append("|---|---|---|---|---|---|---|---|")
    by_id = {
        "3a": {r["id"]: r for r in v3a["per_question"]},
        "3b": {r["id"]: r for r in v3b["per_question"]},
        "3c": {r["id"]: r for r in v3c["per_question"]},
    }
    changed = 0
    for qid in sorted(by_id["3a"]):
        a = by_id["3a"][qid]["score"]["retrieval_score"]
        b = by_id["3b"][qid]["score"]["retrieval_score"]
        c = by_id["3c"][qid]["score"]["retrieval_score"]
        if abs(b - a) < 1e-9 and abs(c - b) < 1e-9:
            continue
        changed += 1
        out.append(
            f"| {qid} | {by_id['3a'][qid]['category']} | "
            f"{a:.3f} | {b:.3f} | {c:.3f} | {b - a:+.3f} | {c - b:+.3f} | {c - a:+.3f} |"
        )
    out.append("")
    out.append(f"_{changed} of 50 questions moved at some stage._")
    return "\n".join(out)


def topk_block(question: dict, stage_label: str) -> str:
    """Render a question's top-K retrieved chunks as a markdown sub-section."""
    lines = []
    lines.append(f"#### {stage_label} — top {len(question['retrieved_chunks'])} retrieved")
    lines.append("")
    lines.append("| rank | rerank | rrf | dense | sparse | source | rel_path | section |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, hit in enumerate(question["retrieved_chunks"], 1):
        rerank = hit.get("rerank")
        rrf = hit.get("rrf")
        dense = hit.get("dense_rank")
        sparse = hit.get("sparse_rank")
        source = hit.get("source", "?")
        rp = hit.get("rel_path", "?")
        sp = (hit.get("section_path") or "")[:90]
        lines.append(
            f"| {i} | "
            f"{rerank:.4f}" + " | " if rerank is not None else " | n/a | "
            + f"{rrf:.4f}" + " | " if rrf is not None else "n/a | "
            + (f"{dense}" if dense is not None else "—") + " | "
            + (f"{sparse}" if sparse is not None else "—") + " | "
            + source + " | " + rp + " | " + sp + " |"
        )
    return "\n".join(lines)


def topk_block_v2(hits: list[dict], header: str) -> str:
    lines = []
    lines.append(f"**{header}**")
    lines.append("")
    lines.append("| rank | rerank | rrf | dense rank | sparse rank | source | rel_path | section_path |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, hit in enumerate(hits, 1):
        rerank = hit.get("rerank")
        rrf = hit.get("rrf")
        rerank_s = f"{rerank:.4f}" if rerank is not None else "—"
        rrf_s = f"{rrf:.4f}" if rrf is not None else "—"
        dense = hit.get("dense_rank")
        dense_s = f"{dense}" if dense is not None else "—"
        sparse = hit.get("sparse_rank")
        sparse_s = f"{sparse}" if sparse is not None else "—"
        source = hit.get("source", "?")
        rp = hit.get("rel_path", "?")
        section = (hit.get("section_path") or "")[:90]
        lines.append(
            f"| {i} | {rerank_s} | {rrf_s} | {dense_s} | {sparse_s} | {source} | `{rp}` | {section} |"
        )
    return "\n".join(lines)


def main():
    BUNDLE.mkdir(parents=True, exist_ok=True)
    v3a = json.loads(V3A.read_text())
    v3b = json.loads(V3B.read_text())
    v3c = json.loads(V3C.read_text())

    # Copy the three result JSONs into the bundle for self-containment
    for src in (V3A, V3B, V3C):
        shutil.copy(src, BUNDLE / src.name)

    # README.md
    readme = []
    readme.append("# Day 3 Engineer Review Bundle")
    readme.append("")
    readme.append("Generated: 2026-05-17")
    readme.append("")
    readme.append("## What is in this bundle")
    readme.append("")
    readme.append("Three retrieval-only eval runs across the Phase 3 stack progression,")
    readme.append("plus diff tables and a deep-dive on the 9 CVE-specific questions whose")
    readme.append("path_recall has been zero from v1 through Phase 3c partial.")
    readme.append("")
    readme.append("### Result JSONs (raw)")
    readme.append("")
    readme.append("| stage | retrieval stack | file |")
    readme.append("|---|---|---|")
    readme.append("| 3a (fixed regex) | Qwen3-Embedding + MiniLM reranker | `2026-05-17_v2-day3a-qwen3emb-fixed-retrieval.json` |")
    readme.append("| 3b | Qwen3-Embedding + Qwen3-Reranker | `2026-05-17_v2-day3b-qwen3rerank-retrieval.json` |")
    readme.append("| 3c partial | Qwen3-Embedding (1,421 contextualized + 12,887 raw) + Qwen3-Reranker | `2026-05-17_v2-day3c-partial-ctx-1421-retrieval.json` |")
    readme.append("")
    readme.append("All three are retrieval-only — no LLM inference. `fact_score` and")
    readme.append("`hallucination_penalty` are `null` on every per-question record.")
    readme.append("`combined` collapses to `retrieval_score` under these conditions.")
    readme.append("")
    readme.append("## Phase 3c PARTIAL — what to know before reading the numbers")
    readme.append("")
    readme.append("3c was abandoned at **1,421 / 14,308 chunks (9.9%)** after the diagnostic")
    readme.append("readout below. Round-robin batch dispatch put the corpus's 9 largest")
    readme.append("sources into the first 9 batches — those 9 sources account for **614 of")
    readme.append("the 1,421 contextualized chunks**. So the partial slice is *biased toward")
    readme.append("high-traffic content*, not a uniform random sample. Interpret the lift")
    readme.append("numbers as an upper-bound on what full-corpus contextualization could")
    readme.append("deliver, per percent of additional coverage.")
    readme.append("")
    readme.append("## Aggregate + per-category retrieval (v1 → v2-Day2 → 3a → 3b → 3c partial)")
    readme.append("")
    try:
        v1 = json.loads(V1_RUBRIC.read_text())
        v2d2 = json.loads(V2D2_RUBRIC.read_text())
        readme.append(diff_table_aggregate([
            ("v1 rubric-patched", v1),
            ("v2 Day2 rubric-patched", v2d2),
            ("3a fixed", v3a),
            ("3b Qwen3-Reranker", v3b),
            ("3c partial", v3c),
        ]))
    except FileNotFoundError:
        readme.append(diff_table_aggregate([
            ("3a fixed", v3a),
            ("3b Qwen3-Reranker", v3b),
            ("3c partial", v3c),
        ]))
    readme.append("")
    readme.append("Reading guide:")
    readme.append("- v1 → v2-Day2: locked-baseline retrieval (same retrieval stack, model swap only)")
    readme.append("- v2-Day2 → 3a fixed: **Qwen3-Embedding swap** (regex fix applied)")
    readme.append("- 3a → 3b: **Qwen3-Reranker swap**")
    readme.append("- 3b → 3c partial: **Contextual Retrieval** (1,421 of 14,308 chunks)")
    readme.append("")
    readme.append("## Per-question movement (only those that changed at some stage)")
    readme.append("")
    readme.append(per_question_movement_changed_only(v3a, v3b, v3c))
    readme.append("")
    readme.append("## Critical readout: the 9 CVE questions with path_recall=0")
    readme.append("")
    readme.append("These are the questions the brief stop-conditions on. Path_recall=0 at")
    readme.append("v1 through 3c partial. **The question for the engineer**: is the right")
    readme.append("CONTENT being retrieved at the wrong path (rubric needs path-broadening),")
    readme.append("or is the right content genuinely absent from the corpus (corpus-pipeline")
    readme.append("memo becomes the trigger)?")
    readme.append("")
    readme.append("See `9-cve-deep-dive.md` for the top-5 retrieved chunks per question at")
    readme.append("each retrieval-stack stage.")
    readme.append("")
    readme.append("## Files in this bundle")
    readme.append("")
    readme.append("| file | content |")
    readme.append("|---|---|")
    readme.append("| `README.md` | this overview |")
    readme.append("| `9-cve-deep-dive.md` | the load-bearing artifact — top-5 retrieved chunks per CVE question per stage |")
    readme.append("| `2026-05-17_v2-day3a-qwen3emb-fixed-retrieval.json` | 3a (fixed-regex) raw result |")
    readme.append("| `2026-05-17_v2-day3b-qwen3rerank-retrieval.json` | 3b raw result |")
    readme.append("| `2026-05-17_v2-day3c-partial-ctx-1421-retrieval.json` | 3c partial raw result |")

    (BUNDLE / "README.md").write_text("\n".join(readme))

    # 9-cve-deep-dive.md
    deep = []
    deep.append("# 9 CVE Deep Dive — top-5 retrieved chunks at each retrieval-stack stage")
    deep.append("")
    deep.append("All 9 questions have `path_recall=0` at every stage from v1 through 3c partial.")
    deep.append("The retrieved-chunks list below shows what the retriever *did* surface for each.")
    deep.append("")
    deep.append("Stack legend:")
    deep.append("- **3a** = Qwen3-Embedding + MiniLM CrossEncoder reranker")
    deep.append("- **3b** = Qwen3-Embedding + Qwen3-Reranker")
    deep.append("- **3c partial** = Qwen3-Embedding (1,421 contextualized chunks) + Qwen3-Reranker")
    deep.append("")
    cve_ids = [r["id"] for r in v3a["per_question"]
               if r["category"] == "cve-specific" and r["score"]["path_recall"] == 0.0]
    a_by = {r["id"]: r for r in v3a["per_question"]}
    b_by = {r["id"]: r for r in v3b["per_question"]}
    c_by = {r["id"]: r for r in v3c["per_question"]}
    for qid in cve_ids:
        q = a_by[qid]
        deep.append(f"## {qid}")
        deep.append("")
        deep.append(f"**Question**: {q['question']}")
        deep.append("")
        deep.append(f"**Category**: {q['category']}")
        deep.append("")
        # gold labels from the original questions file
        gold_substr = []  # not in result file directly; engineer can cross-reference questions.jsonl
        deep.append(f"**Retrieval scores**: 3a={a_by[qid]['score']['retrieval_score']:.3f} | 3b={b_by[qid]['score']['retrieval_score']:.3f} | 3c partial={c_by[qid]['score']['retrieval_score']:.3f}")
        deep.append(f"**Substring recall**: 3a={a_by[qid]['score']['substring_recall']:.3f} | 3b={b_by[qid]['score']['substring_recall']:.3f} | 3c partial={c_by[qid]['score']['substring_recall']:.3f}")
        deep.append("")
        deep.append(topk_block_v2(a_by[qid]["retrieved_chunks"], "3a top-5"))
        deep.append("")
        deep.append(topk_block_v2(b_by[qid]["retrieved_chunks"], "3b top-5"))
        deep.append("")
        deep.append(topk_block_v2(c_by[qid]["retrieved_chunks"], "3c partial top-5 (final stack)"))
        deep.append("")
        deep.append("---")
        deep.append("")
    (BUNDLE / "9-cve-deep-dive.md").write_text("\n".join(deep))

    print(f"Bundle written to: {BUNDLE}")
    for f in sorted(BUNDLE.iterdir()):
        print(f"  {f.name}  ({f.stat().st_size:>10} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
