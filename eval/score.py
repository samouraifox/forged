"""Deterministic scoring for the forged eval harness.

Three sub-scores per question (all in [0.0, 1.0], or None when degenerate):

- retrieval_score: 0.7 * path_recall + 0.3 * substring_recall
- fact_score: matched must_mention_facts / total
- hallucination_penalty: 1.0 - hallucinations / total must_not_hallucinate strings
  (a hallucination is counted only when the forbidden string is in the answer
  AND is not present in retrieved context — substrings that ARE in retrieved
  context are treated as legitimate retrieval-grounded reports)

Per-question combined score: 0.4 * retrieval + 0.4 * fact + 0.2 * hallucination,
with weight renormalization when fact_score or hallucination_penalty is None.
"""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_WEIGHTS: dict[str, float] = {
    "retrieval": 0.4,
    "fact": 0.4,
    "hallucination": 0.2,
}


@dataclass(slots=True)
class QuestionScore:
    retrieval_score: float
    path_recall: float
    substring_recall: float
    fact_score: float | None
    hallucination_penalty: float | None
    hallucinations: list[str]
    combined: float | None


def _ci_in(needle: str, haystack: str) -> bool:
    return needle.lower() in haystack.lower()


def score_retrieval(
    gold_chunk_paths: list[str],
    gold_chunk_substrings: list[str],
    retrieved_hits: list[dict],
) -> tuple[float, float, float]:
    """Returns (retrieval_score, path_recall, substring_recall)."""
    if not retrieved_hits:
        return 0.0, 0.0, 0.0

    retrieved_paths = [str(hit.get("meta", {}).get("rel_path", "")) for hit in retrieved_hits]
    retrieved_texts = [str(hit.get("doc", "")) for hit in retrieved_hits]

    if gold_chunk_paths:
        path_matches = sum(
            1
            for gp in gold_chunk_paths
            if any(_ci_in(gp, rp) for rp in retrieved_paths)
        )
        path_recall = path_matches / len(gold_chunk_paths)
    else:
        path_recall = 1.0

    if gold_chunk_substrings:
        substring_matches = sum(
            1
            for needle in gold_chunk_substrings
            if any(_ci_in(needle, rp) for rp in retrieved_paths)
            or any(_ci_in(needle, rt) for rt in retrieved_texts)
        )
        substring_recall = substring_matches / len(gold_chunk_substrings)
    else:
        substring_recall = 1.0

    retrieval_score = 0.7 * path_recall + 0.3 * substring_recall
    return retrieval_score, path_recall, substring_recall


def score_facts(must_mention_facts: list, answer_text: str) -> float | None:
    """Score each slot in must_mention_facts as a hit (1) or miss (0).

    Slot types:
      - flat string: substring match (case-insensitive) — existing behavior.
      - list[str]:   any-of synonym group; hits if ANY synonym substring matches.
    """
    if not must_mention_facts:
        return None
    hits = 0
    for fact in must_mention_facts:
        if isinstance(fact, list):
            if any(_ci_in(syn, answer_text) for syn in fact):
                hits += 1
        else:
            if _ci_in(fact, answer_text):
                hits += 1
    return hits / len(must_mention_facts)


def score_hallucination(
    must_not_hallucinate: list[str],
    answer_text: str,
    retrieved_hits: list[dict],
) -> tuple[float | None, list[str]]:
    if not must_not_hallucinate:
        return None, []
    context_blob = "\n".join(str(hit.get("doc", "")) for hit in retrieved_hits)
    hallucinated: list[str] = []
    for forbidden in must_not_hallucinate:
        in_answer = _ci_in(forbidden, answer_text)
        in_context = _ci_in(forbidden, context_blob)
        if in_answer and not in_context:
            hallucinated.append(forbidden)
    penalty = 1.0 - (len(hallucinated) / len(must_not_hallucinate))
    return penalty, hallucinated


def combined_score(
    retrieval_score: float,
    fact_score: float | None,
    hallucination_penalty: float | None,
    weights: dict[str, float] | None = None,
) -> float | None:
    w = weights or DEFAULT_WEIGHTS
    pieces: list[tuple[float, float]] = [(retrieval_score, w["retrieval"])]
    if fact_score is not None:
        pieces.append((fact_score, w["fact"]))
    if hallucination_penalty is not None:
        pieces.append((hallucination_penalty, w["hallucination"]))
    total_weight = sum(weight for _, weight in pieces)
    if total_weight == 0:
        return None
    return sum(value * weight for value, weight in pieces) / total_weight


def score_question(
    question: dict,
    retrieved_hits: list[dict],
    answer_text: str,
    weights: dict[str, float] | None = None,
) -> QuestionScore:
    retrieval_score, path_recall, substring_recall = score_retrieval(
        question.get("gold_chunk_paths", []) or [],
        question.get("gold_chunk_substrings", []) or [],
        retrieved_hits,
    )
    fact_score = score_facts(question.get("must_mention_facts", []) or [], answer_text)
    hallucination_penalty, hallucinated = score_hallucination(
        question.get("must_not_hallucinate", []) or [],
        answer_text,
        retrieved_hits,
    )
    combined = combined_score(retrieval_score, fact_score, hallucination_penalty, weights)
    return QuestionScore(
        retrieval_score=retrieval_score,
        path_recall=path_recall,
        substring_recall=substring_recall,
        fact_score=fact_score,
        hallucination_penalty=hallucination_penalty,
        hallucinations=hallucinated,
        combined=combined,
    )


def abstention_precision(per_question: list[dict]) -> tuple[float | None, int]:
    """Mean fact_score among answers that explicitly invoked prior knowledge
    by emitting the [general-knowledge] tag. Tells us how reliable
    prior-weight knowledge is when the model chooses to use it.
    Returns (precision, n_abstained). precision is None if n_abstained == 0
    or if no abstained record has a non-null fact_score."""
    abstained = [
        row for row in per_question
        if "[general-knowledge]" in (row.get("answer_text") or "")
    ]
    facts = [
        row["score"]["fact_score"]
        for row in abstained
        if row["score"]["fact_score"] is not None
    ]
    if not facts:
        return (None, len(abstained))
    return (sum(facts) / len(facts), len(abstained))


def aggregate(per_question: list[dict]) -> dict:
    """Compute mean_* metrics, ignoring None values component-wise."""
    keys = ("retrieval_score", "fact_score", "hallucination_penalty", "combined")
    means: dict[str, float | None] = {}
    for key in keys:
        values = [row["score"][key] for row in per_question if row["score"][key] is not None]
        means[f"mean_{key}"] = sum(values) / len(values) if values else None
    precision, n = abstention_precision(per_question)
    means["abstention_precision"] = precision
    means["n_abstained"] = n
    return means


def aggregate_by_category(per_question: list[dict]) -> dict[str, dict]:
    by_cat: dict[str, list[dict]] = {}
    for row in per_question:
        by_cat.setdefault(row["category"], []).append(row)
    return {cat: aggregate(rows) for cat, rows in by_cat.items()}
