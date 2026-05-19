"""Build a review bundle from rescored eval JSON results.

Engineer-review process rule (added 2026-05-19 after Day 3d engineer feedback):
the README this script generates may only state numbers and rank anomalies.
Any claim about the technical correctness of an answer is the cybersec
engineer's job and must NOT be auto-generated from rubric output. Rubrics are
substring matchers; they cannot tell a right answer from a paraphrased wrong
one. The previous Day 3d bundle inherited rubric blindness by writing
"all 3 chain CVEs cited correctly" — that's the failure mode this refactor
guards against.

Sections in the generated README:
  ## Metrics — aggregates, per-category, and per-baseline deltas. Mechanical.
  ## Open items — questions ranked by metric anomaly. NOT a verdict; a worklist.
  ## Engineer notes — empty placeholder. The engineer fills this in by hand.

Usage:
  python eval/review-bundles/build_bundle.py \
      --current eval/results/<current>.json \
      --baselines v1=eval/results/<v1>.json day2=eval/results/<day2>.json \
      --primaries q-001,q-003,q-004,q-005,q-006,q-007,q-008,q-009,q-010 \
      --out eval/review-bundles/<dated>/

The bundle directory will contain:
  README.md                       — auto-generated, see sections above
  <current-basename>.json         — copy of the rescored result for archive
  per-question-answers.md         — Hermes answer text + raw score numbers
                                    for each --primaries id, for engineer review
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--current", type=Path, required=True,
                        help="Path to the current (most recent) rescored result JSON")
    parser.add_argument("--baselines", nargs="*", default=[],
                        help="name=path pairs for baseline result JSON files, "
                             "e.g. v1=eval/results/X.json day2=eval/results/Y.json")
    parser.add_argument("--primaries", type=str, default="",
                        help="Comma-separated qids to extract Hermes answer text for")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output bundle directory (will be created)")
    parser.add_argument("--label", type=str, default=None,
                        help="Short display label for the current run (defaults to its tag)")
    return parser.parse_args()


def fmt(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def delta(a, b) -> str:
    if a is None or b is None:
        return "n/a"
    return f"{a - b:+.3f}"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def categories_table(current: dict, baselines: dict[str, dict]) -> str:
    by_cat_cur = current.get("aggregate_by_category", {})
    cats = sorted(set(by_cat_cur) | {c for b in baselines.values() for c in b.get("aggregate_by_category", {})})
    metric_keys = ["mean_retrieval_score", "mean_fact_score",
                   "mean_hallucination_penalty", "mean_combined"]

    lines = []
    header = "| category | metric | " + " | ".join(baselines) + " | current |"
    sep = "|---|---|" + "|".join("---" for _ in baselines) + "|---|"
    lines.append(header)
    lines.append(sep)
    for cat in cats:
        for key in metric_keys:
            cur_v = by_cat_cur.get(cat, {}).get(key)
            row = [f"`{cat}`", key.replace("mean_", "")]
            for name, b in baselines.items():
                row.append(fmt(b.get("aggregate_by_category", {}).get(cat, {}).get(key)))
            row.append(fmt(cur_v))
            lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def aggregate_table(current: dict, baselines: dict[str, dict]) -> str:
    keys = ["mean_retrieval_score", "mean_fact_score",
            "mean_hallucination_penalty", "mean_combined",
            "abstention_precision"]
    lines = []
    header = "| metric | " + " | ".join(baselines) + " | current | " \
             + " | ".join(f"Δ vs {n}" for n in baselines) + " |"
    sep = "|---|" + "|".join("---" for _ in baselines) + "|---|" + \
          "|".join("---" for _ in baselines) + "|"
    lines.append(header)
    lines.append(sep)
    for key in keys:
        cur_v = current.get("aggregate", {}).get(key)
        row = [f"`{key}`"]
        baseline_vs = []
        for name, b in baselines.items():
            base_v = b.get("aggregate", {}).get(key)
            row.append(fmt(base_v))
            baseline_vs.append((name, base_v))
        row.append(fmt(cur_v))
        for _, base_v in baseline_vs:
            row.append(delta(cur_v, base_v))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def per_question_deltas_table(current: dict, baselines: dict[str, dict],
                              ids: list[str]) -> str:
    """For named qids, show combined score in current and each baseline."""
    cur_pq = {r["id"]: r for r in current.get("per_question", [])}
    base_pq = {n: {r["id"]: r for r in b.get("per_question", [])}
               for n, b in baselines.items()}

    lines = []
    header = "| qid | category | " + " | ".join(baselines) + " | current |"
    sep = "|---|---|" + "|".join("---" for _ in baselines) + "|---|"
    lines.append(header)
    lines.append(sep)
    for qid in ids:
        r = cur_pq.get(qid)
        if r is None:
            continue
        row = [qid, r.get("category", "")]
        for name in baselines:
            br = base_pq.get(name, {}).get(qid)
            row.append(fmt(br["score"].get("combined") if br else None))
        row.append(fmt(r["score"].get("combined")))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def open_items(current: dict) -> str:
    """Rank questions by metric anomaly. NOT a verdict — a worklist.

    Surfaces three classes (anomalies, not opinions):
      - High-retrieval / low-fact: retrieval >= 0.7 AND fact_score <= 0.45
        Plausible signals: rubric brittleness, generation-side miss, or weak
        chunk-text content. The engineer decides which.
      - Hallucinations recorded: hallucination_penalty < 1.0
      - Timeouts or errors: status != 'ok'
    """
    pq = current.get("per_question", [])
    high_r_low_f = []
    hallucinations = []
    timeouts = []
    for r in pq:
        s = r["score"]
        retr = s.get("retrieval_score") or 0
        fact = s.get("fact_score")
        halluc = s.get("hallucination_penalty")
        if fact is not None and retr >= 0.7 and fact <= 0.45:
            high_r_low_f.append((r["id"], r["category"], retr, fact))
        if halluc is not None and halluc < 1.0:
            hallucinations.append((r["id"], halluc, s.get("hallucinations") or []))
        if r.get("status") and r.get("status") != "ok":
            timeouts.append((r["id"], r.get("status"), r.get("error")))

    high_r_low_f.sort(key=lambda x: x[3])
    hallucinations.sort(key=lambda x: x[1])

    lines = []
    lines.append("### High-retrieval / low-fact (rubric got the chunks but didn't see the facts)")
    lines.append("Anomaly threshold: retrieval ≥ 0.7 AND fact ≤ 0.45. "
                 "Not a verdict — the cause could be rubric brittleness, generation miss, "
                 "or thin chunk content. Engineer judgment required.")
    lines.append("")
    if high_r_low_f:
        lines.append("| qid | category | retrieval | fact |")
        lines.append("|---|---|---|---|")
        for qid, cat, r, f in high_r_low_f:
            lines.append(f"| {qid} | {cat} | {r:.3f} | {f:.3f} |")
    else:
        lines.append("_None._")
    lines.append("")
    lines.append("### Recorded hallucinations (must_not_hallucinate matches)")
    lines.append("")
    if hallucinations:
        lines.append("| qid | hallucination_penalty | hallucinated strings |")
        lines.append("|---|---|---|")
        for qid, h, terms in hallucinations:
            lines.append(f"| {qid} | {h:.3f} | {', '.join(terms)} |")
    else:
        lines.append("_None._")
    lines.append("")
    lines.append("### Non-ok statuses")
    lines.append("")
    if timeouts:
        lines.append("| qid | status | error |")
        lines.append("|---|---|---|")
        for qid, st, err in timeouts:
            lines.append(f"| {qid} | {st} | {err} |")
    else:
        lines.append("_None._")
    return "\n".join(lines)


def primary_answers(current: dict, ids: list[str]) -> str:
    """Pure data extraction. Hermes answer text + score breakdowns.
    No claims about correctness."""
    pq = {r["id"]: r for r in current.get("per_question", [])}
    out_lines: list[str] = []
    out_lines.append("# Per-question answer extracts")
    out_lines.append("")
    out_lines.append("Raw Hermes answer text and score numbers for engineer review. "
                     "No correctness claims; the rubric numbers are deterministic "
                     "substring matches and do not assess technical accuracy.")
    out_lines.append("")
    for qid in ids:
        r = pq.get(qid)
        if r is None:
            continue
        s = r["score"]
        out_lines.append(f"## {qid}")
        out_lines.append("")
        out_lines.append(f"**Category:** {r.get('category', '')}")
        out_lines.append(f"**Question:** {r.get('question', '')}")
        out_lines.append("")
        out_lines.append("**Score breakdown:**")
        out_lines.append("")
        out_lines.append(f"- combined: {fmt(s.get('combined'))}")
        out_lines.append(f"- retrieval_score: {fmt(s.get('retrieval_score'))}")
        out_lines.append(f"- path_recall: {fmt(s.get('path_recall'))}")
        out_lines.append(f"- substring_recall: {fmt(s.get('substring_recall'))}")
        out_lines.append(f"- fact_score: {fmt(s.get('fact_score'))}")
        out_lines.append(f"- hallucination_penalty: {fmt(s.get('hallucination_penalty'))}")
        if s.get("hallucinations"):
            out_lines.append(f"- recorded hallucinations: {s['hallucinations']}")
        out_lines.append("")
        out_lines.append("**Retrieved chunks (top-5):**")
        out_lines.append("")
        for i, h in enumerate(r.get("retrieved_chunks", []), 1):
            rerank = h.get("rerank")
            rerank_s = f"{rerank:.3f}" if rerank is not None else "n/a"
            out_lines.append(f"{i}. `{h.get('rel_path', '')}`  (rerank={rerank_s})")
        out_lines.append("")
        out_lines.append("**Hermes answer text:**")
        out_lines.append("")
        out_lines.append("```")
        out_lines.append(r.get("answer_text") or "(empty)")
        out_lines.append("```")
        out_lines.append("")
    return "\n".join(out_lines)


def main() -> int:
    args = parse_args()

    current = load(args.current)
    baselines: dict[str, dict] = {}
    for spec in args.baselines:
        if "=" not in spec:
            print(f"--baselines entry {spec!r} missing '='", file=sys.stderr)
            return 2
        name, path = spec.split("=", 1)
        baselines[name] = load(Path(path))

    primaries = [pid.strip() for pid in args.primaries.split(",") if pid.strip()]

    args.out.mkdir(parents=True, exist_ok=True)

    # Archive copy of the rescored JSON
    archived = args.out / args.current.name
    shutil.copy2(args.current, archived)

    # README
    label = args.label or current.get("tag", "current")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    qcount = current.get("question_count", "?")
    timeouts = current.get("timeout_count", "?")

    sections = []
    sections.append(f"# Review bundle — {label}")
    sections.append("")
    sections.append(f"Generated: {timestamp}")
    sections.append(f"Source result: `{archived.name}`")
    sections.append(f"Questions: {qcount}    Timeouts: {timeouts}")
    sections.append("")
    sections.append("## Metrics")
    sections.append("")
    sections.append("Aggregate metrics. Numbers only — no claims about answer correctness.")
    sections.append("")
    sections.append(aggregate_table(current, baselines))
    sections.append("")
    sections.append("### Per-category")
    sections.append("")
    sections.append(categories_table(current, baselines))
    sections.append("")
    if primaries:
        sections.append("### Per-question combined score (named primaries)")
        sections.append("")
        sections.append(per_question_deltas_table(current, baselines, primaries))
        sections.append("")
    sections.append("## Open items")
    sections.append("")
    sections.append("Anomaly worklist surfaced from rubric metrics. These are not verdicts. "
                    "The engineer decides what is rubric brittleness, generation miss, "
                    "or corpus gap. See `per-question-answers.md` for raw answer text.")
    sections.append("")
    sections.append(open_items(current))
    sections.append("")
    sections.append("## Engineer notes")
    sections.append("")
    sections.append("_Filled in by cybersec engineer review. Do not auto-generate "
                    "content claims here from rubric output._")
    sections.append("")

    (args.out / "README.md").write_text("\n".join(sections), encoding="utf-8")

    if primaries:
        (args.out / "per-question-answers.md").write_text(
            primary_answers(current, primaries), encoding="utf-8")

    print(f"wrote bundle: {args.out}")
    print(f"  README.md")
    print(f"  {archived.name}")
    if primaries:
        print(f"  per-question-answers.md ({len(primaries)} questions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
