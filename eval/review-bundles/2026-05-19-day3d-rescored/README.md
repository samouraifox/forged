# Review bundle — Day 3d rescored (rubric patches 1a/1b/1c/1d applied)

Generated: 2026-05-19 12:33 UTC
Source result: `2026-05-19_v2-day3d-rescored.json`
Questions: 50    Timeouts: 0

## Metrics

Aggregate metrics. Numbers only — no claims about answer correctness.

| metric | v1 | day2 | day3d_original | current | Δ vs v1 | Δ vs day2 | Δ vs day3d_original |
|---|---|---|---|---|---|---|---|
| `mean_retrieval_score` | 0.652 | 0.652 | 0.872 | 0.873 | +0.221 | +0.221 | +0.001 |
| `mean_fact_score` | 0.348 | 0.466 | 0.529 | 0.546 | +0.199 | +0.081 | +0.018 |
| `mean_hallucination_penalty` | 0.775 | 1.000 | 1.000 | 0.997 | +0.223 | -0.003 | -0.003 |
| `mean_combined` | 0.531 | 0.603 | 0.726 | 0.735 | +0.204 | +0.132 | +0.009 |
| `abstention_precision` | 0.333 | n/a | 0.475 | 0.475 | +0.142 | n/a | +0.000 |

### Per-category

| category | metric | v1 | day2 | day3d_original | current |
|---|---|---|---|---|---|
| `ambiguous` | retrieval_score | 1.000 | 1.000 | 1.000 | 1.000 |
| `ambiguous` | fact_score | 0.133 | 0.300 | 0.233 | 0.300 |
| `ambiguous` | hallucination_penalty | n/a | n/a | n/a | n/a |
| `ambiguous` | combined | 0.567 | 0.650 | 0.617 | 0.650 |
| `attack-technique` | retrieval_score | 0.809 | 0.809 | 0.914 | 0.916 |
| `attack-technique` | fact_score | 0.492 | 0.448 | 0.598 | 0.554 |
| `attack-technique` | hallucination_penalty | 1.000 | 1.000 | 1.000 | 1.000 |
| `attack-technique` | combined | 0.688 | 0.666 | 0.785 | 0.761 |
| `cve-specific` | retrieval_score | 0.160 | 0.160 | 0.955 | 0.955 |
| `cve-specific` | fact_score | 0.195 | 0.220 | 0.505 | 0.588 |
| `cve-specific` | hallucination_penalty | 0.722 | 1.000 | 1.000 | 0.993 |
| `cve-specific` | combined | 0.253 | 0.302 | 0.762 | 0.805 |
| `multi-step` | retrieval_score | 0.603 | 0.603 | 0.732 | 0.732 |
| `multi-step` | fact_score | 0.270 | 0.510 | 0.510 | 0.510 |
| `multi-step` | hallucination_penalty | 0.690 | 1.000 | 1.000 | 1.000 |
| `multi-step` | combined | 0.458 | 0.597 | 0.658 | 0.658 |
| `payload-specific` | retrieval_score | 0.927 | 0.927 | 0.935 | 0.935 |
| `payload-specific` | fact_score | 0.625 | 0.733 | 0.683 | 0.683 |
| `payload-specific` | hallucination_penalty | 1.000 | 1.000 | 1.000 | 1.000 |
| `payload-specific` | combined | 0.788 | 0.843 | 0.817 | 0.817 |

### Per-question combined score (named primaries)

| qid | category | v1 | day2 | day3d_original | current |
|---|---|---|---|---|---|
| q-001 | cve-specific | 0.200 | 0.200 | 0.670 | 0.670 |
| q-003 | cve-specific | 0.200 | 0.200 | 0.867 | 0.867 |
| q-004 | cve-specific | 0.260 | 0.393 | 0.867 | 0.867 |
| q-005 | cve-specific | 0.180 | 0.280 | 0.890 | 0.879 |
| q-006 | cve-specific | 0.037 | 0.037 | 0.833 | 0.800 |
| q-007 | cve-specific | 0.167 | 0.167 | 0.592 | 0.592 |
| q-008 | cve-specific | 0.487 | 0.612 | 1.000 | 1.000 |
| q-009 | cve-specific | 0.100 | 0.200 | 0.570 | 0.703 |
| q-010 | cve-specific | 0.393 | 0.260 | 0.837 | 0.837 |

## Open items

Anomaly worklist surfaced from rubric metrics. These are not verdicts. The engineer decides what is rubric brittleness, generation miss, or corpus gap. See `per-question-answers.md` for raw answer text.

### High-retrieval / low-fact (rubric got the chunks but didn't see the facts)
Anomaly threshold: retrieval ≥ 0.7 AND fact ≤ 0.45. Not a verdict — the cause could be rubric brittleness, generation miss, or thin chunk content. Engineer judgment required.

| qid | category | retrieval | fact |
|---|---|---|---|
| q-033 | multi-step | 0.800 | 0.000 |
| q-046 | ambiguous | 1.000 | 0.000 |
| q-050 | ambiguous | 1.000 | 0.000 |
| q-001 | cve-specific | 0.925 | 0.250 |
| q-022 | attack-technique | 0.925 | 0.250 |
| q-025 | attack-technique | 0.850 | 0.250 |
| q-007 | cve-specific | 0.850 | 0.333 |
| q-009 | cve-specific | 0.925 | 0.333 |
| q-011 | payload-specific | 0.850 | 0.333 |
| q-015 | payload-specific | 1.000 | 0.333 |
| q-019 | payload-specific | 0.850 | 0.333 |
| q-024 | attack-technique | 0.850 | 0.333 |
| q-030 | multi-step | 0.850 | 0.333 |
| q-036 | multi-step | 1.000 | 0.333 |
| q-049 | ambiguous | 1.000 | 0.333 |

### Recorded hallucinations (must_not_hallucinate matches)

| qid | hallucination_penalty | hallucinated strings |
|---|---|---|
| q-005 | 0.944 | CVE-2021-34474 |

### Non-ok statuses

_None._

## Engineer notes

_Filled in by cybersec engineer review. Do not auto-generate content claims here from rubric output._
