#!/usr/bin/env python3
"""Re-score a cached v1 result JSON against an updated questions.jsonl,
optionally splicing in recovered records for previously-timed-out questions.
No model calls. Retrieval chunk doc text is rehydrated from chroma by chunk id.

Usage:
    python eval/rescore.py \
        --questions eval/questions.jsonl \
        --in eval/results/<old>.json \
        --recover eval/results/<recover>.json \
        --out eval/results/<new>.json \
        --tag v1-baseline-50q-final
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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

import chromadb  # noqa: E402
import score as scoring  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument(
        "--in",
        dest="in_path",
        type=Path,
        required=True,
        help="Source result JSON to re-score",
    )
    parser.add_argument(
        "--recover",
        type=Path,
        default=None,
        help="Optional second result JSON; records here overwrite same-id "
        "records in --in whose status was 'timeout'",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tag", type=str, required=True)
    parser.add_argument(
        "--db",
        type=Path,
        default=REPO_ROOT / "rag" / "chroma_db",
        help="Chroma DB path for rehydrating chunk doc text",
    )
    parser.add_argument("--collection", type=str, default="security")
    return parser.parse_args()


def load_questions(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        out[obj["id"]] = obj
    return out


def load_result(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class DocCache:
    """Lazy chunk-id -> doc-text lookup against chroma."""

    def __init__(self, db_path: Path, collection: str) -> None:
        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_collection(collection)
        self._cache: dict[str, str] = {}

    def fetch(self, chunk_ids: list[str]) -> dict[str, str]:
        missing = [cid for cid in chunk_ids if cid not in self._cache and cid is not None]
        if missing:
            got = self.collection.get(ids=missing, include=["documents"])
            for cid, doc in zip(got["ids"], got["documents"]):
                self._cache[cid] = doc or ""
            # Any chunk id not returned from chroma — record as empty so we
            # don't loop forever on a missing id, but flag.
            returned = set(got["ids"])
            for cid in missing:
                if cid not in returned:
                    self._cache[cid] = ""
                    print(f"[warn] chunk id {cid} not found in collection", file=sys.stderr)
        return {cid: self._cache.get(cid, "") for cid in chunk_ids if cid is not None}


def rehydrate_hits(summary_hits: list[dict], cache: DocCache) -> list[dict]:
    """Convert _hit_summary dicts back into score-compatible hit dicts with
    'doc' and 'meta' restored. doc text is fetched from chroma by chunk id."""
    ids = [h.get("id") for h in summary_hits if h.get("id")]
    docs = cache.fetch(ids)
    rebuilt: list[dict] = []
    for h in summary_hits:
        cid = h.get("id")
        rebuilt.append(
            {
                "id": cid,
                "doc": docs.get(cid, "") if cid else "",
                "meta": {
                    "rel_path": h.get("rel_path"),
                    "source": h.get("source"),
                    "section_path": h.get("section_path"),
                },
                "rerank": h.get("rerank"),
                "rrf": h.get("rrf"),
                "dense_rank": h.get("dense_rank"),
                "sparse_rank": h.get("sparse_rank"),
            }
        )
    return rebuilt


def rescore_record(record: dict, question: dict, cache: DocCache) -> dict:
    """Recompute score fields against current question definition. Preserves
    answer_text, thinking_text, retrieved_chunks (summary form), status,
    timeout, wall_clock_s, error."""
    if record.get("timeout") or record.get("status") == "timeout":
        # Keep null scoring; no model output to score.
        return record

    answer_text = record.get("answer_text") or ""
    summary_hits = record.get("retrieved_chunks") or []
    hits = rehydrate_hits(summary_hits, cache)
    qs = scoring.score_question(question, hits, answer_text)
    record = dict(record)
    record["score"] = {
        "retrieval_score": qs.retrieval_score,
        "path_recall": qs.path_recall,
        "substring_recall": qs.substring_recall,
        "fact_score": qs.fact_score,
        "hallucination_penalty": qs.hallucination_penalty,
        "hallucinations": qs.hallucinations,
        "combined": qs.combined,
    }
    return record


def main() -> int:
    args = parse_args()
    questions = load_questions(args.questions)
    src = load_result(args.in_path)

    recover_map: dict[str, dict] = {}
    if args.recover is not None:
        rec = load_result(args.recover)
        for r in rec.get("per_question", []):
            recover_map[r["id"]] = r

    cache = DocCache(args.db, args.collection)

    rescored: list[dict] = []
    overwritten: list[str] = []
    for record in src["per_question"]:
        qid = record["id"]
        was_timeout = bool(record.get("timeout")) or record.get("status") == "timeout"
        if was_timeout and qid in recover_map:
            new_record = recover_map[qid]
            overwritten.append(qid)
        else:
            new_record = record
        rescored.append(rescore_record(new_record, questions[qid], cache))

    # Add any recover records whose id isn't in the source (shouldn't happen
    # for our flow, but stay tolerant).
    src_ids = {r["id"] for r in src["per_question"]}
    for qid, rec in recover_map.items():
        if qid not in src_ids:
            rescored.append(rescore_record(rec, questions[qid], cache))
            overwritten.append(qid)

    aggregate = scoring.aggregate(rescored)
    aggregate_by_category = scoring.aggregate_by_category(rescored)
    timeout_count = sum(1 for r in rescored if r.get("timeout"))

    now = datetime.now(timezone.utc)
    payload = {
        "tag": args.tag,
        "timestamp_utc": now.isoformat(),
        "model": src.get("model"),
        "config": {
            "rescored_from": str(args.in_path),
            "recover_from": str(args.recover) if args.recover else None,
            "questions_path": str(args.questions),
            "db_path": str(args.db),
        },
        "question_count": len(rescored),
        "timeout_count": timeout_count,
        "total_wall_clock_s": sum(r.get("wall_clock_s", 0.0) or 0.0 for r in rescored),
        "mean_per_question_s": (
            sum(r.get("wall_clock_s", 0.0) or 0.0 for r in rescored) / max(1, len(rescored))
        ),
        "aggregate": aggregate,
        "aggregate_by_category": aggregate_by_category,
        "per_question": rescored,
        "overwritten_from_recover": overwritten,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"rescored {len(rescored)} records; overwrote from recover: {overwritten}")
    print(f"wrote {args.out}")
    print()
    print(f"aggregate:")
    for k, v in aggregate.items():
        if v is None:
            print(f"  {k}: n/a")
        else:
            print(f"  {k}: {v:.3f}")
    print(f"  timeouts: {timeout_count}")
    print()
    print(f"per category:")
    for cat, ag in aggregate_by_category.items():
        bits = []
        for k in ("mean_retrieval_score", "mean_fact_score", "mean_hallucination_penalty", "mean_combined"):
            v = ag.get(k)
            bits.append(f"{k.replace('mean_','')}={'n/a' if v is None else f'{v:.3f}'}")
        print(f"  {cat:<18} " + "  ".join(bits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
