#!/usr/bin/env python3
"""Diff two eval result files.

Usage:
    python eval/compare.py path/to/baseline.json path/to/latest.json

Reports:
  - Aggregate deltas (mean_retrieval_score, mean_fact_score,
    mean_hallucination_penalty, mean_combined).
  - Questions where the per-question combined score changed by >= 0.1.
  - Newly-failing questions: combined was >= 0.5 in baseline and < 0.5 in latest.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


COMBINED_DELTA_THRESHOLD = 0.10
FAILING_THRESHOLD = 0.50


def load_result(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _delta(base: float | None, latest: float | None) -> str:
    if base is None or latest is None:
        return "n/a"
    diff = latest - base
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:.3f}"


def index_by_id(result: dict) -> dict[str, dict]:
    return {row["id"]: row for row in result.get("per_question", [])}


def print_aggregate_delta(base: dict, latest: dict) -> None:
    print("=" * 72)
    print(f"baseline: {base.get('tag')}  {base.get('timestamp_utc')}")
    print(f"latest:   {latest.get('tag')}  {latest.get('timestamp_utc')}")
    print(f"model baseline -> latest: {base.get('model')!r} -> {latest.get('model')!r}")
    print("-" * 72)
    base_agg = base["aggregate"]
    latest_agg = latest["aggregate"]
    rows = [
        ("mean_retrieval_score", "retrieval"),
        ("mean_fact_score", "fact"),
        ("mean_hallucination_penalty", "halluc"),
        ("mean_combined", "combined"),
    ]
    for key, label in rows:
        b = base_agg.get(key)
        l = latest_agg.get(key)
        print(f"  {label:<10}  baseline={_fmt(b)}  latest={_fmt(l)}  delta={_delta(b, l)}")
    print("-" * 72)


def print_per_category_delta(base: dict, latest: dict) -> None:
    base_cats = base.get("aggregate_by_category", {})
    latest_cats = latest.get("aggregate_by_category", {})
    cats = sorted(set(base_cats) | set(latest_cats))
    print("per category (combined):")
    for cat in cats:
        b = base_cats.get(cat, {}).get("mean_combined")
        l = latest_cats.get(cat, {}).get("mean_combined")
        print(f"  {cat:<18}  baseline={_fmt(b)}  latest={_fmt(l)}  delta={_delta(b, l)}")
    print("-" * 72)


def print_question_deltas(base: dict, latest: dict) -> None:
    base_idx = index_by_id(base)
    latest_idx = index_by_id(latest)
    ids = sorted(set(base_idx) | set(latest_idx))
    moved: list[tuple[str, float | None, float | None, float]] = []
    newly_failing: list[tuple[str, float | None, float | None]] = []
    for qid in ids:
        b = base_idx.get(qid)
        l = latest_idx.get(qid)
        if b is None or l is None:
            continue
        b_combined = b["score"]["combined"]
        l_combined = l["score"]["combined"]
        if b_combined is None or l_combined is None:
            continue
        diff = l_combined - b_combined
        if abs(diff) >= COMBINED_DELTA_THRESHOLD:
            moved.append((qid, b_combined, l_combined, diff))
        if b_combined >= FAILING_THRESHOLD and l_combined < FAILING_THRESHOLD:
            newly_failing.append((qid, b_combined, l_combined))

    moved.sort(key=lambda row: row[3])
    print(f"questions with |delta_combined| >= {COMBINED_DELTA_THRESHOLD:.2f}: {len(moved)}")
    for qid, b, l, diff in moved:
        sign = "+" if diff >= 0 else ""
        print(f"  {qid:<14}  {_fmt(b)} -> {_fmt(l)}  ({sign}{diff:.3f})")
    print("-" * 72)
    print(f"newly failing (combined dropped below {FAILING_THRESHOLD:.2f}): {len(newly_failing)}")
    for qid, b, l in newly_failing:
        print(f"  {qid:<14}  {_fmt(b)} -> {_fmt(l)}")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("baseline", type=Path)
    parser.add_argument("latest", type=Path)
    args = parser.parse_args()

    base = load_result(args.baseline)
    latest = load_result(args.latest)

    print_aggregate_delta(base, latest)
    print_per_category_delta(base, latest)
    print_question_deltas(base, latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
