"""Phase 3c.1 dispatcher helper: pick next batch, audit outputs, persist state.

Usage:
  python rag/contextualize/runner.py next-batch [--size N] [--strategy idx|big-first|round-robin]
      → prints the next batch of source indices (one per line) and writes them
        to state.json's "in_flight" list. Used by the builder turn to spawn
        subagents.
  python rag/contextualize/runner.py absorb-batch
      → reads any source_NNNN_contexts.json that's been written, audits, appends
        passing entries to contexts.jsonl, flags failed/sanitized entries to
        fallback_queue.jsonl, updates state.json. Idempotent.
  python rag/contextualize/runner.py status
      → prints progress summary.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MAIN = Path("rag/contextualize/main")
STATE_PATH = Path("rag/contextualize/state.json")
CONTEXTS_PATH = Path("rag/contextualize/contexts.jsonl")
FALLBACK_PATH = Path("rag/contextualize/fallback_queue.jsonl")

# Banned-phrase auditor list. Phase 3c.0 smoke surfaced four over-broad
# entries ("to mitigate", "to prevent", "to defend against", "to protect
# against") that false-positived on legitimate cybersec descriptions
# (the chunks themselves describe mitigation/prevention controls).
# Orchestrator approved their removal; everything else from the brief stays.
BANNED_PHRASES = [
    # Authorization hedges
    "ensure you have authorization", "ensure authorization",
    "with proper authorization", "with permission",
    "responsible disclosure", "responsibly disclose",
    "ethical hacking",
    "for educational purposes", "for learning purposes", "for academic purposes",
    "use responsibly", "act responsibly",
    # Sanitization markers
    "[redacted]", "[sanitized]", "[content removed]",
    "i cannot", "i can't", "i should not", "i won't",
    # Soft refusal
    "consider alternative", "more constructive", "harm reduction",
]


def audit(ctx: str) -> tuple[bool, list[str]]:
    c = ctx.lower()
    flagged = [p for p in BANNED_PHRASES if p in c]
    return (len(flagged) == 0, flagged)


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    manifest = json.loads((MAIN / "manifest.json").read_text())
    return {
        "manifest_count": len(manifest),
        "completed": [],  # list of source idx ints
        "in_flight": [],
        "failed": [],
    }


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=1))


def cmd_status() -> int:
    state = load_state()
    n = state["manifest_count"]
    done = len(state["completed"])
    inflight = len(state["in_flight"])
    failed = len(state["failed"])
    pending = n - done - inflight
    ctx_lines = 0
    if CONTEXTS_PATH.exists():
        ctx_lines = sum(1 for _ in CONTEXTS_PATH.open())
    fallback_lines = 0
    if FALLBACK_PATH.exists():
        fallback_lines = sum(1 for _ in FALLBACK_PATH.open())
    print(f"sources: {n} total | {done} done | {inflight} in-flight | {failed} failed | {pending} pending")
    print(f"contexts.jsonl entries: {ctx_lines}")
    print(f"fallback_queue.jsonl entries: {fallback_lines}")
    return 0


def cmd_next_batch(size: int, strategy: str) -> int:
    state = load_state()
    manifest = json.loads((MAIN / "manifest.json").read_text())
    done_set = set(state["completed"])
    inflight_set = set(state["in_flight"])
    pending = [m for m in manifest if m["idx"] not in done_set and m["idx"] not in inflight_set]
    if not pending:
        print("(no pending sources)", file=sys.stderr)
        return 0
    if strategy == "big-first":
        pending.sort(key=lambda m: -m["chunk_count"])
    elif strategy == "round-robin":
        # one big + (size-1) small, then repeat
        big = sorted(pending, key=lambda m: -m["chunk_count"])
        small = sorted(pending, key=lambda m: m["chunk_count"])
        # build interleaved list
        order = []
        while big or small:
            if big:
                order.append(big.pop(0))
            for _ in range(size - 1):
                if small:
                    order.append(small.pop(0))
                else:
                    break
        pending = order
    # default 'idx' strategy: already in idx order from manifest

    batch = pending[:size]
    state["in_flight"] = list(set(state["in_flight"]) | {m["idx"] for m in batch})
    save_state(state)
    # Print one idx per line for the builder to consume
    for m in batch:
        print(f"{m['idx']:04d}\t{m['chunk_count']}\t{m['source']}/{m['rel_path']}")
    return 0


def cmd_absorb_batch() -> int:
    state = load_state()
    in_flight = list(state["in_flight"])
    new_completed = []
    new_failed = []
    new_contexts: list[dict] = []
    new_fallback: list[dict] = []

    for idx in in_flight:
        ctx_path = MAIN / f"source_{idx:04d}_contexts.json"
        chunks_path = MAIN / f"source_{idx:04d}_chunks.json"
        if not ctx_path.exists():
            # subagent hasn't completed (or failed) — leave in flight
            continue
        try:
            data = json.loads(ctx_path.read_text())
            chunk_meta = json.loads(chunks_path.read_text())
            expected_ids = [c["chunk_id"] for c in chunk_meta]
        except Exception as e:
            new_failed.append({"idx": idx, "reason": f"parse error: {e}"})
            continue
        # validate shape
        if not isinstance(data, list) or len(data) != len(expected_ids):
            new_failed.append({"idx": idx, "reason": f"len mismatch: got {len(data)}, expected {len(expected_ids)}"})
            continue
        # audit + collect
        for entry, expected_id in zip(data, expected_ids):
            cid = entry.get("chunk_id")
            ctx = entry.get("context", "")
            if cid != expected_id:
                new_failed.append({"idx": idx, "reason": f"chunk_id mismatch: {cid} vs {expected_id}"})
                break
            ok, fl = audit(ctx)
            row = {"chunk_id": cid, "context": ctx, "source_model": "claude-subagent", "src_idx": idx}
            if ok:
                new_contexts.append(row)
            else:
                row["flagged_phrases"] = fl
                new_fallback.append(row)
        else:
            new_completed.append(idx)

    # write outputs
    if new_contexts:
        with CONTEXTS_PATH.open("a") as h:
            for r in new_contexts:
                h.write(json.dumps(r) + "\n")
    if new_fallback:
        with FALLBACK_PATH.open("a") as h:
            for r in new_fallback:
                h.write(json.dumps(r) + "\n")

    state["completed"] = sorted(set(state["completed"]) | set(new_completed))
    state["in_flight"] = [i for i in state["in_flight"] if i not in set(new_completed)]
    state["failed"].extend(new_failed)
    save_state(state)

    print(
        f"absorbed: {len(new_completed)} sources done, {len(new_contexts)} contexts "
        f"appended, {len(new_fallback)} flagged-for-fallback, {len(new_failed)} failed"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    nb = sub.add_parser("next-batch")
    nb.add_argument("--size", type=int, default=10)
    nb.add_argument("--strategy", choices=["idx", "big-first", "round-robin"], default="round-robin")
    sub.add_parser("absorb-batch")
    args = ap.parse_args()
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "next-batch":
        return cmd_next_batch(args.size, args.strategy)
    if args.cmd == "absorb-batch":
        return cmd_absorb_batch()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
