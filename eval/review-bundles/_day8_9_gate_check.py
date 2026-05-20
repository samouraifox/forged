#!/usr/bin/env python3
"""Day 8-9 gate verification.

Loads adaptive-eval result JSON, compares to Day 3d rescored baseline,
emits gate-by-gate pass/fail report. Hand-audit columns kept where the
gate needs human judgment (gate 1 audit).

Usage:
    python eval/review-bundles/_day8_9_gate_check.py \
        --adaptive eval/results/<adaptive>.json \
        --baseline eval/review-bundles/2026-05-19-day3d-rescored/2026-05-19_v2-day3d-rescored.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Rough category → expected branch mapping. Used for gate 1 accuracy audit
# only; the classifier is judged against this prior, not bound by it.
EXPECTED_BRANCH = {
    "cve-specific": "easy",
    "payload-specific": "easy",
    "attack-technique": "easy",  # mostly single-technique entities
    "multi-step": "hard",
    "ambiguous": "hard",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def fmt(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def gate1_classify(adaptive: dict) -> None:
    print("\n=== Gate 1 — classify accuracy + branch distribution ===")
    pq = adaptive["per_question"]
    total = len(pq)
    easy = sum(1 for r in pq if (r.get("adaptive") or {}).get("branch") == "easy")
    hard = sum(1 for r in pq if (r.get("adaptive") or {}).get("branch") == "hard")
    print(f"Total: {total}  EASY: {easy} ({easy/total*100:.0f}%)  HARD: {hard} ({hard/total*100:.0f}%)")

    matches = 0
    mismatches: list[tuple[str, str, str, str]] = []
    for r in pq:
        cat = r["category"]
        expected = EXPECTED_BRANCH.get(cat, "easy")
        actual = (r.get("adaptive") or {}).get("branch")
        if actual == expected:
            matches += 1
        else:
            mismatches.append((r["id"], cat, expected, actual))
    accuracy = matches / total if total else 0.0
    print(f"Classifier accuracy vs prior: {matches}/{total} ({accuracy*100:.0f}%)")
    print(f"Gate 1 (≥80% accuracy): {'PASS' if accuracy >= 0.80 else 'FAIL'}")
    if mismatches:
        print("Mismatches (qid, category, expected, actual):")
        for qid, cat, exp, act in mismatches[:20]:
            print(f"  {qid:8} {cat:18} expected={exp:4} actual={act}")


def gate2_easy_no_regression(adaptive: dict, baseline: dict) -> None:
    print("\n=== Gate 2 — EASY-branch no regression (±0.01 of baseline) ===")
    base_pq = {r["id"]: r for r in baseline["per_question"]}
    diffs = []
    for r in adaptive["per_question"]:
        if (r.get("adaptive") or {}).get("branch") != "easy":
            continue
        b = base_pq.get(r["id"])
        if b is None:
            continue
        a_r = r["score"]["retrieval_score"]
        b_r = b["score"]["retrieval_score"]
        a_c = r["score"]["combined"]
        b_c = b["score"]["combined"]
        if a_r is None or b_r is None or a_c is None or b_c is None:
            continue
        diffs.append((r["id"], a_r - b_r, a_c - b_c))

    if not diffs:
        print("No EASY-classified questions with comparable baselines")
        return
    max_r_drop = min(d[1] for d in diffs)
    max_c_drop = min(d[2] for d in diffs)
    worst_r = sorted(diffs, key=lambda x: x[1])[:5]
    worst_c = sorted(diffs, key=lambda x: x[2])[:5]
    print(f"EASY count: {len(diffs)}")
    print(f"max retrieval delta: {max_r_drop:+.3f}    max combined delta: {max_c_drop:+.3f}")
    if max_r_drop < -0.01 or max_c_drop < -0.01:
        print("Gate 2: FAIL")
    else:
        print("Gate 2: PASS")
    print("worst retrieval Δ:")
    for qid, dr, dc in worst_r:
        print(f"  {qid}: Δretr={dr:+.3f}  Δcombined={dc:+.3f}")
    print("worst combined Δ:")
    for qid, dr, dc in worst_c:
        print(f"  {qid}: Δretr={dr:+.3f}  Δcombined={dc:+.3f}")


def gate3_hard_movement(adaptive: dict, baseline: dict) -> None:
    print("\n=== Gate 3 — HARD-branch aggregate lift (≥+0.03 combined) ===")
    base_pq = {r["id"]: r for r in baseline["per_question"]}
    hard_a = []
    hard_b = []
    per_q = []
    for r in adaptive["per_question"]:
        if (r.get("adaptive") or {}).get("branch") != "hard":
            continue
        b = base_pq.get(r["id"])
        if b is None:
            continue
        a_c = r["score"]["combined"]
        b_c = b["score"]["combined"]
        if a_c is None or b_c is None:
            continue
        hard_a.append(a_c)
        hard_b.append(b_c)
        per_q.append((r["id"], r["category"], a_c, b_c, a_c - b_c))
    if not hard_a:
        print("No HARD-classified questions")
        return
    mean_a = sum(hard_a) / len(hard_a)
    mean_b = sum(hard_b) / len(hard_b)
    print(f"HARD count: {len(hard_a)}")
    print(f"mean combined: baseline={mean_b:.3f}  adaptive={mean_a:.3f}  Δ={mean_a - mean_b:+.3f}")
    print(f"Gate 3 (Δ ≥ +0.03): {'PASS' if (mean_a - mean_b) >= 0.03 else 'FAIL'}")
    print("per-question deltas (sorted by Δ):")
    for qid, cat, a, b, d in sorted(per_q, key=lambda x: -x[4]):
        print(f"  {qid:8} {cat:18} base={b:.3f} adp={a:.3f} Δ={d:+.3f}")


def gate4_q007(adaptive: dict) -> None:
    print("\n=== Gate 4 — q-007 specific ===")
    pq = {r["id"]: r for r in adaptive["per_question"]}
    r = pq.get("q-007")
    if r is None:
        print("q-007 not in result set")
        return
    adp = r.get("adaptive") or {}
    branch = adp.get("branch")
    decision = adp.get("classify_decision")
    rewrites = adp.get("rewritten_queries", [])
    hyde = adp.get("hyde_doc") or ""
    print(f"branch={branch}  decision={decision}  retry_count={adp.get('retry_count')}")
    print(f"avg_relevance={adp.get('avg_relevance')}")
    print("rewrites:")
    for i, q in enumerate(rewrites, 1):
        print(f"  {i}. {q[:200]}")
    print(f"hyde_doc ({len(hyde)} chars): {hyde[:200]}{'...' if len(hyde) > 200 else ''}")

    # Mandiant chunk indicator
    final_paths = [h.get("rel_path", "") for h in r.get("retrieved_chunks", [])]
    print("final_context top-5:")
    for i, p in enumerate(final_paths, 1):
        print(f"  {i}. {p}")
    mandiant_present = any("mandiant" in p.lower() for p in final_paths)
    webshell_in_rewrites = any(
        kw in (q.lower() + " ".join(rewrites).lower())
        for kw in ("webshell", "web shell", "human2.aspx", "lemurloot", "ioc", "indicator")
        for q in rewrites
    ) or any(
        kw in " ".join(rewrites).lower()
        for kw in ("webshell", "web shell", "human2.aspx", "lemurloot", "ioc", "indicator")
    )
    print(f"  mandiant chunk in final_context: {'YES' if mandiant_present else 'NO'}")
    print(f"  webshell/IoC keyword in rewrites: {'YES' if webshell_in_rewrites else 'NO'}")
    is_hard = branch == "hard"
    gate4 = is_hard and mandiant_present
    print(f"Gate 4 (HARD + Mandiant in final_context): {'PASS' if gate4 else 'FAIL'}  "
          f"[webshell-rewrite={'YES' if webshell_in_rewrites else 'NO'}]")


def gate6_latency(adaptive: dict, baseline: dict) -> None:
    print("\n=== Gate 6 — wallclock latency ===")
    base_pq = {r["id"]: r for r in baseline["per_question"]}
    easy_ratios = []
    hard_ratios = []
    for r in adaptive["per_question"]:
        b = base_pq.get(r["id"])
        if b is None or b.get("wall_clock_s") is None:
            continue
        ratio = (r["wall_clock_s"] or 0) / max(1.0, b["wall_clock_s"])
        if (r.get("adaptive") or {}).get("branch") == "easy":
            easy_ratios.append((r["id"], ratio, r["wall_clock_s"], b["wall_clock_s"]))
        else:
            hard_ratios.append((r["id"], ratio, r["wall_clock_s"], b["wall_clock_s"]))
    if easy_ratios:
        mean_easy = sum(x[1] for x in easy_ratios) / len(easy_ratios)
        max_easy = max(x[1] for x in easy_ratios)
        print(f"EASY wallclock ratio mean={mean_easy:.2f}× max={max_easy:.2f}× "
              f"(brief target ≤1.5×)")
    if hard_ratios:
        mean_hard = sum(x[1] for x in hard_ratios) / len(hard_ratios)
        max_hard = max(x[1] for x in hard_ratios)
        print(f"HARD wallclock ratio mean={mean_hard:.2f}× max={max_hard:.2f}× "
              f"(brief target ≤2-3×)")
    easy_pass = (not easy_ratios) or max(x[1] for x in easy_ratios) <= 1.5
    hard_pass = (not hard_ratios) or max(x[1] for x in hard_ratios) <= 3.0
    print(f"Gate 6: {'PASS' if easy_pass and hard_pass else 'FAIL'}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adaptive", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args()
    adaptive = load(args.adaptive)
    baseline = load(args.baseline)

    print(f"Adaptive: {args.adaptive.name}  Q={adaptive['question_count']}")
    print(f"Baseline: {args.baseline.name}  Q={baseline['question_count']}")
    print()
    print("Aggregate:")
    a = adaptive["aggregate"]
    b = baseline["aggregate"]
    for k in ("mean_retrieval_score", "mean_fact_score",
              "mean_hallucination_penalty", "mean_combined"):
        print(f"  {k:30} base={fmt(b.get(k))}  adp={fmt(a.get(k))}  "
              f"Δ={fmt((a.get(k) or 0) - (b.get(k) or 0))}")

    gate1_classify(adaptive)
    gate2_easy_no_regression(adaptive, baseline)
    gate3_hard_movement(adaptive, baseline)
    gate4_q007(adaptive)
    gate6_latency(adaptive, baseline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
