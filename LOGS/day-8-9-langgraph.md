# Phase B Day 8-9 — LangGraph adaptive RAG state machine

**Date:** 2026-05-20
**Predecessor:** Phase 3.5+2 q-007 MOVEit operator-anchor ingestion (`LOGS/q-007-moveit-ingestion.md`)
**Outcome:** HOLD for orchestrator review. The 10q smoke failed gates 1, 2, 5 (classifier accuracy, HARD-output coherence, q-007-specific gate). Full 50q **NOT** launched.
**Smoke report:** `LOGS/day-8-9-langgraph-smoke.md` — gate verdicts, per-question facts, diagnoses, six remediation options (none applied).

---

## Goal

Replace the linear `query → embed → hybrid_search → rerank → top-k → generate` pipeline with a LangGraph state machine that routes by difficulty:

- **EASY** queries (CVE ID, tool name, single technique) → fast linear path identical to current behavior.
- **HARD** queries (multi-topic, comparative, exploratory, ambiguous) → multi-query rewriting + HyDE + union retrieval + CRAG relevance grading + at most one retry.

Motivation: Phase 3.5+2 q-007 close-out demonstrated that a single-strategy pipeline cannot adaptively expand a multi-topic query ("SQLi-to-RCE chain + post-exploitation IoCs"). The fix at the corpus layer (ingest more chunks) created chain-vs-IoC competition for top-5 slots and the IoC anchors got pushed out of context. An adaptive layer that issues multiple semantic angles (e.g., "Cl0p webshell deployment", "MOVEit IoCs", "human2.aspx") can recombine evidence across angles.

## Architecture

### Locked V2 stack

- Hermes-4-14B Q6_K via llama-server, YaRN-64K, `--cache-type-k q4_0 --cache-type-v q4_0` (Q4 KV per brief, applied via direct launch — `scripts/llama-server.sh` has Q8 baked in; left unchanged this turn).
- Qwen3-Embedding-0.6B (BATCH=16, MAX_LEN=2048) — OpenVINO INT8 on Arc 140V.
- Qwen3-Reranker-0.6B (BATCH=4, MAX_LEN=1024, truncation_side="left") — OpenVINO INT8.
- Chroma collection `forged_v2_qwen3_emb_cve_full` (14,425 chunks, post-Phase-3.5+2).
- BM25 sparse index.
- llama-server flags this run: `--jinja -c 65536 --rope-scaling yarn --yarn-orig-ctx 32768 --cache-type-k q4_0 --cache-type-v q4_0 -ngl 999 --temp 0.4`.

### LangGraph state

`GraphState` (pydantic v2):

```
query: str
branch: Literal["easy", "hard"] | None
rewritten_queries: list[str]
hyde_doc: str | None
retrieved_chunks: list[dict]     # hit dicts from hybrid_search/rerank
relevance_grades: dict[str, float]
avg_relevance: float | None
retry_count: int                 # MAX 1
final_context: list[dict]
answer: str | None
# Telemetry (additive beyond brief):
classify_decision: str | None
timing: dict[str, float]
status_log: list[str]
thinking_text: str
```

Telemetry fields (`classify_decision`, `timing`, `status_log`, `thinking_text`) are additive vs. the brief — they're needed to validate gates 1, 5, 6 from outside the graph and to surface adaptive metadata to the eval bundle.

### Nodes

| Node | LLM call? | Purpose |
|---|---|---|
| `classify_query` | yes (~4 tok, no-think) | EASY/HARD decision |
| `retrieve_simple` | no | `RetrieveService.retrieve_top_hits()` — baseline path |
| `multi_query_rewrite` | yes (~200 tok, no-think) | 2-3 paraphrasings of original query |
| `retrieve_with_hyde` | yes (~300 tok, no-think) | hypothetical-answer doc → hybrid_search on doc |
| `retrieve_multi_query` | no | union(HyDE, original, rewrites) → rerank against ORIGINAL → top-5 |
| `grade_relevance` | yes (~4 tok × N, no-think) | per-chunk YES/NO; avg_relevance = fraction YES |
| `increment_retry` | no | bumps `retry_count` (LangGraph edges can't mutate state) |
| `generate_answer` | yes (full stream, think on) | final RAG answer |

### Edges

```
START → classify_query
classify_query → retrieve_simple        (branch == easy)
                → multi_query_rewrite    (branch == hard)
multi_query_rewrite → retrieve_with_hyde → retrieve_multi_query → grade_relevance
retrieve_simple → grade_relevance
grade_relevance → generate_answer        (avg_relevance ≥ 0.5  OR  retry_count ≥ 1)
                → increment_retry        (avg_relevance < 0.5  AND  retry_count < 1)
increment_retry → multi_query_rewrite    (with "previous attempt failed" hint)
generate_answer → END
```

Note: easy-branch also passes through `grade_relevance`. The expected case is `avg_relevance ≥ 0.5` → straight to generate. If CRAG ever fires retry on an easy question, the question semantically becomes HARD (multi-query+HyDE applied). This is intentional — CRAG is a quality gate, not a branch annotation.

### Auxiliary-call think suppression

The locked stack has no out-of-band think toggle on llama-server. We use the same prompt-policy approach as `service.py` (`NO_THINK_INSTRUCTION` system suffix). Observed in the wire smoke: Hermes still emits `<think>` blocks for auxiliary calls (eval rate ~2.2 t/s vs ~4.4 t/s when answering short YES/NO with no thinking). `_strip_think` removes the `<think>` blocks from auxiliary responses before parsing, so quality is unaffected. Latency is higher than ideal — see gate 6 below.

## Implementation files

- `rag/adaptive_pipeline.py` (new) — GraphState + 7 nodes + `build_adaptive_graph()` + `attach_service()`.
- `rag/service.py` — adds `RetrieveService.adaptive_query(question) → dict`. Reuses module-level OpenAI client wired to the same `LLM_BASE_URL`.
- `eval/run_eval.py` — adds `--adaptive` flag. When set, routes via `service.adaptive_query()` and records `adaptive` metadata block per question (branch, classify_decision, rewritten_queries, hyde_doc, relevance_grades, avg_relevance, retry_count, timing).
- `rag/requirements.txt` — adds `langgraph>=0.2,<0.3` and `pydantic>=2.0`.

## Wire smoke (single question, q-001)

Verified end-to-end before the full 10q smoke.

```
q-001 (Spring4Shell): classify=HARD → multi_query (2 variants) → HyDE (350 chars)
                       → multi_retrieve (top-5) → grade (avg=0.80) → generate
combined=0.670 (retrieval=0.925, fact=0.250, halluc=1.000)
wall_clock=226s, timings: classify=3s, multi_query=39s, hyde=58s,
                          multi_retrieve=10s, grade=11s, generate=104s
```

The retrieval and combined scores match the Phase 3.5+2 baseline for q-001 (retrieval=0.925, fact=0.250). The HARD path did not degrade the score — but did not improve it either. Q-001 was a planned-EASY candidate; classifier mis-routed it. Smoke-results section below tracks classification accuracy.

## 10q smoke — see smoke report

Full results, per-question metadata, and gate verdicts are in `LOGS/day-8-9-langgraph-smoke.md`. Summary:

- 5 planned EASY: q-001 (HARD), q-003 (EASY), q-008 (HARD), q-012 (HARD), q-018 (HARD) — 1/5 correct
- 5 planned HARD: q-007 (HARD), q-029 (HARD), q-035 (HARD), q-038 (TIMEOUT), q-046 (HARD) — 4/5 correct (excluding timeout)
- Overall classifier accuracy: 5/9 = 56% (gate 1 threshold ≥80%, FAIL)
- q-007 specific: HARD ✓, no webshell variant ✗, no Mandiant chunk in final_context ✗ (gate 5 FAIL)
- Memory peak 26 GB used / 4 GB swap, matches Day 3d (gate 3 PASS)
- Latency: 1 timeout (q-038) and q-008 at 3.54× exceed budgets (gate 4 FAIL)

## 50q eval

Not launched. Per orchestrator: hold until remediation is approved.

## Deferred for orchestrator decision

The smoke report documents six non-applied remediation options (A-F). Most defensible from gate evidence: option E (drop HyDE + CRAG; keep classify + multi-query) or option F (reconsider whether HARD branching is the right layer for adaptive logic — agent-loop in Pydantic AI / Day 10+ might be where this work belongs).
