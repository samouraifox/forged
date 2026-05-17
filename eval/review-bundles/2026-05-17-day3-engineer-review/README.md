# Day 3 Engineer Review Bundle

Generated: 2026-05-17

## What is in this bundle

Three retrieval-only eval runs across the Phase 3 stack progression,
plus diff tables and a deep-dive on the 9 CVE-specific questions whose
path_recall has been zero from v1 through Phase 3c partial.

### Result JSONs (raw)

| stage | retrieval stack | file |
|---|---|---|
| 3a (fixed regex) | Qwen3-Embedding + MiniLM reranker | `2026-05-17_v2-day3a-qwen3emb-fixed-retrieval.json` |
| 3b | Qwen3-Embedding + Qwen3-Reranker | `2026-05-17_v2-day3b-qwen3rerank-retrieval.json` |
| 3c partial | Qwen3-Embedding (1,421 contextualized + 12,887 raw) + Qwen3-Reranker | `2026-05-17_v2-day3c-partial-ctx-1421-retrieval.json` |

All three are retrieval-only — no LLM inference. `fact_score` and
`hallucination_penalty` are `null` on every per-question record.
`combined` collapses to `retrieval_score` under these conditions.

## Phase 3c PARTIAL — what to know before reading the numbers

3c was abandoned at **1,421 / 14,308 chunks (9.9%)** after the diagnostic
readout below. Round-robin batch dispatch put the corpus's 9 largest
sources into the first 9 batches — those 9 sources account for **614 of
the 1,421 contextualized chunks**. So the partial slice is *biased toward
high-traffic content*, not a uniform random sample. Interpret the lift
numbers as an upper-bound on what full-corpus contextualization could
deliver, per percent of additional coverage.

## Aggregate + per-category retrieval (v1 → v2-Day2 → 3a → 3b → 3c partial)

| category | v1 rubric-patched | v2 Day2 rubric-patched | 3a fixed | 3b Qwen3-Reranker | 3c partial |
|---|---|---|---|---|---|
| ambiguous | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| attack-technique | 0.809 | 0.809 | 0.897 | 0.925 | 0.916 |
| cve-specific | 0.160 | 0.160 | 0.168 | 0.190 | 0.190 |
| multi-step | 0.603 | 0.603 | 0.599 | 0.578 | 0.691 |
| payload-specific | 0.927 | 0.927 | 0.927 | 0.945 | 0.935 |
| **OVERALL** | **0.652** | **0.652** | **0.666** | **0.671** | **0.706** |

Reading guide:
- v1 → v2-Day2: locked-baseline retrieval (same retrieval stack, model swap only)
- v2-Day2 → 3a fixed: **Qwen3-Embedding swap** (regex fix applied)
- 3a → 3b: **Qwen3-Reranker swap**
- 3b → 3c partial: **Contextual Retrieval** (1,421 of 14,308 chunks)

## Per-question movement (only those that changed at some stage)

| id | category | 3a | 3b | 3c partial | Δ(3b−3a) | Δ(3c−3b) | Δ(3c−3a) |
|---|---|---|---|---|---|---|---|
| q-006 | cve-specific | 0.075 | 0.150 | 0.150 | +0.075 | +0.000 | +0.075 |
| q-007 | cve-specific | 0.000 | 0.075 | 0.075 | +0.075 | +0.000 | +0.075 |
| q-009 | cve-specific | 0.075 | 0.150 | 0.150 | +0.075 | +0.000 | +0.075 |
| q-011 | payload-specific | 0.775 | 0.850 | 0.850 | +0.075 | +0.000 | +0.075 |
| q-013 | payload-specific | 0.800 | 0.900 | 0.800 | +0.100 | -0.100 | +0.000 |
| q-025 | attack-technique | 0.850 | 0.925 | 0.850 | +0.075 | -0.075 | +0.000 |
| q-026 | attack-technique | 0.925 | 1.000 | 1.000 | +0.075 | +0.000 | +0.075 |
| q-027 | attack-technique | 0.925 | 1.000 | 1.000 | +0.075 | +0.000 | +0.075 |
| q-029 | multi-step | 0.850 | 0.925 | 0.925 | +0.075 | +0.000 | +0.075 |
| q-030 | multi-step | 0.775 | 0.850 | 0.850 | +0.075 | +0.000 | +0.075 |
| q-032 | multi-step | 0.300 | 0.225 | 0.225 | -0.075 | +0.000 | -0.075 |
| q-034 | multi-step | 0.850 | 0.850 | 0.500 | +0.000 | -0.350 | -0.350 |
| q-035 | multi-step | 0.925 | 0.225 | 0.925 | -0.700 | +0.700 | +0.000 |
| q-037 | multi-step | 0.850 | 1.000 | 1.000 | +0.150 | +0.000 | +0.150 |
| q-038 | multi-step | 0.150 | 0.225 | 0.925 | +0.075 | +0.700 | +0.775 |
| q-039 | multi-step | 0.150 | 0.150 | 0.850 | +0.000 | +0.700 | +0.700 |
| q-040 | multi-step | 0.300 | 0.200 | 0.300 | -0.100 | +0.100 | +0.000 |
| q-041 | multi-step | 0.075 | 0.225 | 0.225 | +0.150 | +0.000 | +0.150 |
| q-043 | multi-step | 1.000 | 0.925 | 1.000 | -0.075 | +0.075 | +0.000 |
| q-045 | multi-step | 0.850 | 0.925 | 0.925 | +0.075 | +0.000 | +0.075 |

_20 of 50 questions moved at some stage._

## Critical readout: the 9 CVE questions with path_recall=0

These are the questions the brief stop-conditions on. Path_recall=0 at
v1 through 3c partial. **The question for the engineer**: is the right
CONTENT being retrieved at the wrong path (rubric needs path-broadening),
or is the right content genuinely absent from the corpus (corpus-pipeline
memo becomes the trigger)?

See `9-cve-deep-dive.md` for the top-5 retrieved chunks per question at
each retrieval-stack stage.

## Files in this bundle

| file | content |
|---|---|
| `README.md` | this overview |
| `9-cve-deep-dive.md` | the load-bearing artifact — top-5 retrieved chunks per CVE question per stage |
| `2026-05-17_v2-day3a-qwen3emb-fixed-retrieval.json` | 3a (fixed-regex) raw result |
| `2026-05-17_v2-day3b-qwen3rerank-retrieval.json` | 3b raw result |
| `2026-05-17_v2-day3c-partial-ctx-1421-retrieval.json` | 3c partial raw result |