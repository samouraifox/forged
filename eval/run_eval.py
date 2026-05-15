#!/usr/bin/env python3
"""Run the forged eval harness against the live v1 RAG stack.

Loads questions.jsonl, drives each question through RetrieveService, scores
retrieval and answer text deterministically, writes a timestamped JSON result
file in eval/results/, and prints a one-screen summary.

Usage (from repo root):
    python eval/run_eval.py --questions eval/questions.jsonl --include-examples --tag smoke

The script will re-exec itself under rag/venv/bin/python so the v1 dependency
set (chromadb, ollama, sentence-transformers, bm25s) is always available.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PY = REPO_ROOT / "rag" / "venv" / "bin" / "python"


def _reexec_under_venv() -> None:
    if not VENV_PY.exists():
        return
    venv_root = (REPO_ROOT / "rag" / "venv").resolve()
    if Path(sys.prefix).resolve() == venv_root:
        return
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])


_reexec_under_venv()

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Imports below this line require the v1 venv.
from rag import runtime as rag_runtime  # noqa: E402
from rag.service import (  # noqa: E402
    QueryConfig,
    QueryEventType,
    RetrieveService,
    LLM_DISPLAY_NAME,
)
import score as scoring  # noqa: E402


def _parse_on_off(value: str) -> bool:
    v = value.strip().lower()
    if v in {"on", "true", "1", "yes"}:
        return True
    if v in {"off", "false", "0", "no"}:
        return False
    raise argparse.ArgumentTypeError(f"expected on|off, got {value!r}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path(__file__).resolve().parent / "questions.jsonl",
        help="Path to questions.jsonl",
    )
    parser.add_argument("--topk", type=int, default=5)
    parser.add_argument("--rag", type=_parse_on_off, default=True, help="on|off")
    parser.add_argument("--think", type=_parse_on_off, default=False, help="on|off — default off for speed")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--tag", type=str, default="baseline")
    parser.add_argument("--include-examples", action="store_true")
    parser.add_argument(
        "--db",
        type=Path,
        default=REPO_ROOT / "rag" / "chroma_db",
        help="Path to the Chroma DB directory",
    )
    parser.add_argument("--show-progress", action="store_true", default=True)
    return parser.parse_args()


def load_questions(path: Path, include_examples: bool) -> list[dict]:
    questions: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {error}")
            if obj.get("is_example") and not include_examples:
                continue
            questions.append(obj)
    return questions


def _hit_summary(hit: dict) -> dict:
    meta = hit.get("meta") or {}
    return {
        "id": hit.get("id"),
        "rel_path": meta.get("rel_path"),
        "source": meta.get("source"),
        "section_path": meta.get("section_path"),
        "rerank": hit.get("rerank"),
        "rrf": hit.get("rrf"),
        "dense_rank": hit.get("dense_rank"),
        "sparse_rank": hit.get("sparse_rank"),
    }


def run_one(
    service: RetrieveService,
    question_obj: dict,
    config: QueryConfig,
) -> dict:
    question_text = question_obj["question"]
    t0 = time.perf_counter()

    top_hits_raw = service.retrieve_top_hits(question_text, config, history=[]) if config.rag else []

    answer_chunks: list[str] = []
    thinking_chunks: list[str] = []
    status_lines: list[str] = []
    timing_lines: list[str] = []
    error_text: str | None = None

    try:
        for event in service.stream_query(question_text, config, history=[]):
            if event.type == QueryEventType.ANSWER_CHUNK:
                answer_chunks.append(event.text)
            elif event.type == QueryEventType.THINKING:
                thinking_chunks.append(event.text)
            elif event.type == QueryEventType.STATUS:
                status_lines.append(event.text)
                if "[timing]" in event.text:
                    timing_lines.append(event.text)
            elif event.type == QueryEventType.ERROR:
                error_text = event.text
            elif event.type == QueryEventType.DONE:
                continue
    except Exception as exc:
        error_text = f"{type(exc).__name__}: {exc}"

    wall_clock = time.perf_counter() - t0
    answer_text = "".join(answer_chunks)
    thinking_text = "".join(thinking_chunks)

    qs = scoring.score_question(question_obj, top_hits_raw, answer_text)

    return {
        "id": question_obj["id"],
        "category": question_obj["category"],
        "question": question_text,
        "retrieved_chunks": [_hit_summary(hit) for hit in top_hits_raw],
        "answer_text": answer_text,
        "thinking_text": thinking_text,
        "timing_status": timing_lines,
        "wall_clock_s": wall_clock,
        "error": error_text,
        "score": {
            "retrieval_score": qs.retrieval_score,
            "path_recall": qs.path_recall,
            "substring_recall": qs.substring_recall,
            "fact_score": qs.fact_score,
            "hallucination_penalty": qs.hallucination_penalty,
            "hallucinations": qs.hallucinations,
            "combined": qs.combined,
        },
    }


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def print_summary(results: dict) -> None:
    agg = results["aggregate"]
    print()
    print("=" * 72)
    print(f"forged eval — tag={results['tag']}  model={results['model']}")
    print(f"questions: {results['question_count']}  wall_clock: {results['total_wall_clock_s']:.1f} s")
    print("-" * 72)
    print(f"  mean_retrieval_score      : {_fmt(agg['mean_retrieval_score'])}")
    print(f"  mean_fact_score           : {_fmt(agg['mean_fact_score'])}")
    print(f"  mean_hallucination_penalty: {_fmt(agg['mean_hallucination_penalty'])}")
    print(f"  mean_combined             : {_fmt(agg['mean_combined'])}")
    print("-" * 72)
    print("per category:")
    for cat, cat_agg in results["aggregate_by_category"].items():
        print(
            f"  {cat:<18} retrieval={_fmt(cat_agg['mean_retrieval_score'])}  "
            f"fact={_fmt(cat_agg['mean_fact_score'])}  "
            f"halluc={_fmt(cat_agg['mean_hallucination_penalty'])}  "
            f"combined={_fmt(cat_agg['mean_combined'])}"
        )
    print("-" * 72)
    ranked = sorted(
        results["per_question"],
        key=lambda row: (row["score"]["combined"] if row["score"]["combined"] is not None else 0.0),
    )
    print("top 3 worst (by combined):")
    for row in ranked[:3]:
        print(f"  [{row['id']:<14}] combined={_fmt(row['score']['combined'])}  {row['question'][:80]}")
    print("=" * 72)
    print(f"result file: {results['result_path']}")


def main() -> int:
    args = parse_args()
    questions = load_questions(args.questions, args.include_examples)
    if args.limit is not None:
        questions = questions[: args.limit]
    if not questions:
        print("no questions to evaluate (use --include-examples to run the smoke set)", file=sys.stderr)
        return 2

    rag_runtime.ensure_ollama_running(status_callback=lambda message: print(f"[runtime] {message}", flush=True))

    service = RetrieveService(db_path=str(args.db))
    config = QueryConfig(
        think=args.think,
        rag=args.rag,
        topk=args.topk,
    )

    per_question: list[dict] = []
    overall_t0 = time.perf_counter()
    for index, question_obj in enumerate(questions, 1):
        if args.show_progress:
            print(f"[{index}/{len(questions)}] {question_obj['id']}: {question_obj['question'][:80]}", flush=True)
        per_question.append(run_one(service, question_obj, config))
    total_wall_clock_s = time.perf_counter() - overall_t0

    aggregate = scoring.aggregate(per_question)
    aggregate_by_category = scoring.aggregate_by_category(per_question)

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d_%H%M")
    result_dir = Path(__file__).resolve().parent / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / f"{stamp}_{args.tag}.json"

    payload = {
        "tag": args.tag,
        "timestamp_utc": now.isoformat(),
        "model": LLM_DISPLAY_NAME,
        "config": {
            "topk": args.topk,
            "rag": args.rag,
            "think": args.think,
            "include_examples": args.include_examples,
            "questions_path": str(args.questions),
            "db_path": str(args.db),
        },
        "question_count": len(per_question),
        "total_wall_clock_s": total_wall_clock_s,
        "mean_per_question_s": total_wall_clock_s / max(1, len(per_question)),
        "aggregate": aggregate,
        "aggregate_by_category": aggregate_by_category,
        "per_question": per_question,
    }

    result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    payload["result_path"] = str(result_path)
    print_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
