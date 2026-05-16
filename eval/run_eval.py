#!/usr/bin/env python3
"""Run the forged eval harness against the live v1 RAG stack.

Loads questions.jsonl, drives each question through RetrieveService, scores
retrieval and answer text deterministically, writes a timestamped JSON result
file in eval/results/, and prints a one-screen summary.

Usage (from repo root):
    python eval/run_eval.py --questions eval/questions.jsonl --include-examples --tag smoke

The script will re-exec itself under rag/venv/bin/python so the v1 dependency
set (chromadb, ollama, sentence-transformers, bm25s) is always available.

Hardening (added 2026-05-16 after a v1-stack hang):
- Per-question 300s timeout via a one-shot ThreadPoolExecutor; on timeout
  the question is recorded with null scores and the run continues.
- Incremental writes to eval/results/partial-<tag>.jsonl with fsync after
  each question — any future hang is recoverable.
- --resume <partial-file>: skip ids already present in the partial file,
  and roll those records into the final aggregate.
- Live status line per question: [q-NNN | cat] status=X combined=Y in Zs.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PY = REPO_ROOT / "rag" / "venv" / "bin" / "python"

# Default per-question wallclock budget. Includes hidden <think> generation
# under --think on, so set higher than the original 300s payload-only budget.
PER_QUESTION_TIMEOUT_S = 600.0


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
    parser.add_argument(
        "--think",
        type=_parse_on_off,
        default=True,
        help="on|off — default on so <think> content is captured and stuck-in-think loops are visible",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--tag", type=str, default="baseline")
    parser.add_argument("--include-examples", action="store_true")
    parser.add_argument(
        "--db",
        type=Path,
        default=REPO_ROOT / "rag" / "chroma_db",
        help="Path to the Chroma DB directory",
    )
    parser.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="Path to an existing partial-<tag>.jsonl to resume from",
    )
    parser.add_argument(
        "--per-question-timeout",
        type=float,
        default=PER_QUESTION_TIMEOUT_S,
        help="Seconds before a question is recorded as timed out (default 600)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Short alias that overrides --per-question-timeout when set",
    )
    parser.add_argument(
        "--ids",
        type=str,
        default=None,
        help="Comma-separated question-ID filter (e.g. q-001,q-015). Runs inference only on the listed ids.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Override result-file path (default: results/<timestamp>_<tag>.json)",
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


def load_partial(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as error:
                raise SystemExit(f"{path}:{line_number}: invalid partial JSONL: {error}")
    return records


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
        "status": "ok",
        "timeout": False,
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


def timeout_record(question_obj: dict, timeout_s: float) -> dict:
    return {
        "id": question_obj["id"],
        "category": question_obj["category"],
        "question": question_obj["question"],
        "retrieved_chunks": [],
        "answer_text": "",
        "thinking_text": "",
        "timing_status": [],
        "wall_clock_s": timeout_s,
        "error": f"timeout after {timeout_s:.0f}s",
        "status": "timeout",
        "timeout": True,
        "score": {
            "retrieval_score": None,
            "path_recall": None,
            "substring_recall": None,
            "fact_score": None,
            "hallucination_penalty": None,
            "hallucinations": [],
            "combined": None,
        },
    }


def run_with_timeout(
    service: RetrieveService,
    question_obj: dict,
    config: QueryConfig,
    timeout_s: float,
) -> dict:
    """Run a single question in a daemon worker thread. If it doesn't return
    within timeout_s, fabricate a timeout record and move on. The worker
    thread is allowed to leak (CPython cannot kill threads cleanly); each
    question gets its own one-shot executor so leaked threads don't block
    subsequent work."""
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="eval-q")
    future = executor.submit(run_one, service, question_obj, config)
    try:
        return future.result(timeout=timeout_s)
    except FutTimeout:
        return timeout_record(question_obj, timeout_s)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _kill_ollama_runner() -> int:
    """Kill the ollama model-runner subprocess (the child of `ollama serve`
    that holds the model + KV cache in memory). `ollama serve` will respawn
    a fresh runner on the next request, with a clean inference slot.
    Returns the number of killed PIDs."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "ollama runner"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return 0
    pids = [int(p) for p in result.stdout.split() if p.strip().isdigit()]
    killed = 0
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            killed += 1
        except ProcessLookupError:
            pass
    return killed


def _append_partial(partial_path: Path, record: dict) -> None:
    with partial_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def print_summary(results: dict) -> None:
    agg = results["aggregate"]
    print()
    print("=" * 72)
    print(f"forged eval — tag={results['tag']}  model={results['model']}")
    print(
        f"questions: {results['question_count']}  "
        f"timeouts: {results.get('timeout_count', 0)}  "
        f"wall_clock: {results['total_wall_clock_s']:.1f} s"
    )
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
    print("top 5 worst (by combined):")
    for row in ranked[:5]:
        flag = " [TIMEOUT]" if row.get("timeout") else ""
        print(
            f"  [{row['id']:<14}] combined={_fmt(row['score']['combined'])}{flag}  "
            f"{row['question'][:80]}"
        )
    print("=" * 72)
    print(f"result file: {results['result_path']}")


def main() -> int:
    args = parse_args()
    if args.timeout is not None:
        args.per_question_timeout = args.timeout
    questions = load_questions(args.questions, args.include_examples)
    if args.ids:
        wanted = {qid.strip() for qid in args.ids.split(",") if qid.strip()}
        missing = wanted - {q["id"] for q in questions}
        if missing:
            print(f"--ids referenced ids not found in questions file: {sorted(missing)}", file=sys.stderr)
            return 2
        questions = [q for q in questions if q["id"] in wanted]
    if args.limit is not None:
        questions = questions[: args.limit]
    if not questions:
        print("no questions to evaluate (use --include-examples to run the smoke set)", file=sys.stderr)
        return 2

    result_dir = Path(__file__).resolve().parent / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    partial_path = args.resume if args.resume is not None else result_dir / f"partial-{args.tag}.jsonl"

    resumed_records: list[dict] = []
    completed_ids: set[str] = set()
    if args.resume is not None:
        resumed_records = load_partial(args.resume)
        completed_ids = {r["id"] for r in resumed_records}
        print(f"[resume] loaded {len(resumed_records)} prior records from {args.resume}", flush=True)
    elif partial_path.exists():
        # Fresh tag but a stale partial file exists; refuse to silently overwrite.
        raise SystemExit(
            f"partial file {partial_path} already exists. "
            f"Use --resume {partial_path} to continue, or delete it to start over."
        )

    pending = [q for q in questions if q["id"] not in completed_ids]
    print(
        f"[plan] total={len(questions)} resumed={len(resumed_records)} "
        f"pending={len(pending)} timeout={args.per_question_timeout:.0f}s",
        flush=True,
    )

    rag_runtime.ensure_ollama_running(status_callback=lambda message: print(f"[runtime] {message}", flush=True))

    service = RetrieveService(db_path=str(args.db))
    config = QueryConfig(
        think=args.think,
        rag=args.rag,
        topk=args.topk,
    )

    per_question: list[dict] = list(resumed_records)
    overall_t0 = time.perf_counter()
    for index, question_obj in enumerate(pending, 1):
        if args.show_progress:
            print(
                f"[{index}/{len(pending)}] {question_obj['id']}: "
                f"{question_obj['question'][:80]}",
                flush=True,
            )
        record = run_with_timeout(service, question_obj, config, args.per_question_timeout)
        _append_partial(partial_path, record)
        per_question.append(record)
        combined = record["score"]["combined"]
        status_label = "TIMEOUT" if record.get("timeout") else "ok"
        print(
            f"[{record['id']} | {record['category']}] {status_label} "
            f"combined={_fmt(combined)} in {record['wall_clock_s']:.1f}s",
            flush=True,
        )
        if record.get("timeout"):
            # The orphaned worker thread is still recv()-blocked on a socket
            # to ollama. With OLLAMA_NUM_PARALLEL=1 the next question would
            # queue behind the never-completing request and also time out.
            # Killing the ollama runner subprocess force-closes that slot;
            # ollama serve will respawn a fresh runner on the next request.
            killed = _kill_ollama_runner()
            print(
                f"[recovery] timeout fired; killed {killed} ollama runner(s) "
                f"to clear stuck slot",
                flush=True,
            )
            time.sleep(2)
            rag_runtime.ensure_ollama_running(
                status_callback=lambda message: print(f"[runtime] {message}", flush=True),
            )
    total_wall_clock_s = time.perf_counter() - overall_t0

    aggregate = scoring.aggregate(per_question)
    aggregate_by_category = scoring.aggregate_by_category(per_question)
    timeout_count = sum(1 for r in per_question if r.get("timeout"))

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d_%H%M")
    result_path = args.out if args.out is not None else result_dir / f"{stamp}_{args.tag}.json"

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
            "per_question_timeout_s": args.per_question_timeout,
            "resumed_from": str(args.resume) if args.resume else None,
            "partial_path": str(partial_path),
        },
        "question_count": len(per_question),
        "timeout_count": timeout_count,
        "total_wall_clock_s": total_wall_clock_s,
        "mean_per_question_s": total_wall_clock_s / max(1, len(pending)),
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
