# Review bundle — Phase 3.5+2 — q-007 MOVEit operator-anchor ingestion (retrieval-only)

Generated: 2026-05-20 10:14 UTC
Source result: `2026-05-19_day3.5+2-moveit-retrieval.json`
Questions: 50    Timeouts: 0

## Metrics

Aggregate metrics. Numbers only — no claims about answer correctness.

| metric | day3.5_final | current | Δ vs day3.5_final |
|---|---|---|---|
| `mean_retrieval_score` | 0.873 | 0.873 | +0.000 |
| `mean_fact_score` | n/a | n/a | n/a |
| `mean_hallucination_penalty` | n/a | n/a | n/a |
| `mean_combined` | 0.873 | 0.873 | +0.000 |
| `abstention_precision` | n/a | n/a | n/a |

### Per-category

| category | metric | day3.5_final | current |
|---|---|---|---|
| `ambiguous` | retrieval_score | 1.000 | 1.000 |
| `ambiguous` | fact_score | n/a | n/a |
| `ambiguous` | hallucination_penalty | n/a | n/a |
| `ambiguous` | combined | 1.000 | 1.000 |
| `attack-technique` | retrieval_score | 0.916 | 0.916 |
| `attack-technique` | fact_score | n/a | n/a |
| `attack-technique` | hallucination_penalty | n/a | n/a |
| `attack-technique` | combined | 0.916 | 0.916 |
| `cve-specific` | retrieval_score | 0.955 | 0.955 |
| `cve-specific` | fact_score | n/a | n/a |
| `cve-specific` | hallucination_penalty | n/a | n/a |
| `cve-specific` | combined | 0.955 | 0.955 |
| `multi-step` | retrieval_score | 0.732 | 0.732 |
| `multi-step` | fact_score | n/a | n/a |
| `multi-step` | hallucination_penalty | n/a | n/a |
| `multi-step` | combined | 0.732 | 0.732 |
| `payload-specific` | retrieval_score | 0.935 | 0.935 |
| `payload-specific` | fact_score | n/a | n/a |
| `payload-specific` | hallucination_penalty | n/a | n/a |
| `payload-specific` | combined | 0.935 | 0.935 |

### Per-question combined score (named primaries)

| qid | category | day3.5_final | current |
|---|---|---|---|
| q-001 | cve-specific | 0.925 | 0.925 |
| q-003 | cve-specific | 1.000 | 1.000 |
| q-004 | cve-specific | 1.000 | 1.000 |
| q-005 | cve-specific | 0.925 | 0.925 |
| q-006 | cve-specific | 1.000 | 1.000 |
| q-007 | cve-specific | 0.850 | 0.850 |
| q-008 | cve-specific | 1.000 | 1.000 |
| q-009 | cve-specific | 0.925 | 0.925 |
| q-010 | cve-specific | 0.925 | 0.925 |

## Open items

Anomaly worklist surfaced from rubric metrics. These are not verdicts. The engineer decides what is rubric brittleness, generation miss, or corpus gap. See `per-question-answers.md` for raw answer text.

### High-retrieval / low-fact (rubric got the chunks but didn't see the facts)
Anomaly threshold: retrieval ≥ 0.7 AND fact ≤ 0.45. Not a verdict — the cause could be rubric brittleness, generation miss, or thin chunk content. Engineer judgment required.

_None._

### Recorded hallucinations (must_not_hallucinate matches)

_None._

### Non-ok statuses

_None._

## Engineer notes

_Filled in by cybersec engineer review. Do not auto-generate content claims here from rubric output._
