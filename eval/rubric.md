# Scoring Rubric

The eval harness produces three deterministic per-question scores (all 0.0–1.0) and a weighted combined score. This rubric documents what those scores measure and how to read them.

## retrieval_score (0.4 of combined)

How well the retrieval layer surfaces the chunks that should answer the question. Blended:

- `path_recall = matched gold_chunk_paths in top-k / len(gold_chunk_paths)`
  - "Matched" = the gold path string is a substring of some retrieved chunk's `meta.rel_path`.
- `substring_recall = matched gold_chunk_substrings in top-k / len(gold_chunk_substrings)`
  - "Matched" = the substring (case-insensitive) appears in `meta.rel_path` OR the chunk body for at least one retrieved chunk.
- `retrieval_score = 0.7 * path_recall + 0.3 * substring_recall`

A retrieval_score of 1.0 means every gold signal landed in top-k. 0.0 means nothing relevant came back. Path matches dominate because they're stricter.

## fact_score (0.4 of combined)

How completely the answer mentions the must-mention facts.

- `fact_score = matched / len(must_mention_facts)`
- Match = case-insensitive substring presence in the answer text (`<think>` content excluded).
- Empty `must_mention_facts` → score is null and excluded from aggregation (weight redistributes).

A high fact_score with a low retrieval_score means the model is answering from prior weights — fine on easy questions, a hallucination risk on niche ones.

## hallucination_penalty (0.2 of combined)

Subtractive measure of confabulation.

- For each string in `must_not_hallucinate`:
  - If it appears in any retrieved chunk text, it does NOT count as a hallucination (the model legitimately reported retrieved info — possibly wrong, but at least grounded).
  - If it does NOT appear in retrieved context but DOES appear in the answer, it counts as a hallucination.
- `hallucination_penalty = 1.0 - (hallucinations / len(must_not_hallucinate))`
- Empty `must_not_hallucinate` → null, excluded from aggregation.

A hallucination_penalty of 1.0 means clean. Below 0.8 = the model is inventing things even when the retrieval gave it nothing to support them.

## Combined score

Default weights: 0.4 retrieval + 0.4 fact + 0.2 hallucination.

When either fact_score or hallucination_penalty is null, the missing weight is redistributed proportionally across the surviving components. If all three are null (degenerate question), combined is null.

## How to read a result

- **combined ≥ 0.8** → answer is well-grounded and well-formed for this question.
- **0.5 ≤ combined < 0.8** → partial credit. Inspect which sub-score dragged it down.
- **combined < 0.5** → failing question. Either retrieval missed, the model under-answered, or it confabulated.

## What this rubric does NOT measure

- Style, voice, structure of the answer.
- Whether the answer is actionable in practice.
- Reasoning quality on multi-step questions.
- Calibration on ambiguous questions.

These require LLM-as-judge or manual review and are explicitly out of scope for the deterministic harness. Future expansion may add an optional LLM-judge layer that produces a fourth score; the deterministic three remain the primary gate.

## Manual-review notes

For each question's `ideal_answer_outline`, compare the streamed answer text to the outline and grade on:

1. **Coverage** — did the answer hit the major steps in the outline?
2. **Ordering** — is the operator sequence correct (recon before exploitation, verification before pivot, etc.)?
3. **Specificity** — does it cite concrete commands/payloads/flags or hand-wave?
4. **Verification step** — does it include a way to confirm success?

Manual grades are not auto-aggregated. Keep notes per question in a separate review log.
