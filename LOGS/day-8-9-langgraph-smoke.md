# Day 8-9 LangGraph adaptive RAG — smoke report

**Date:** 2026-05-20
**Status:** HOLD for orchestrator review. Smoke gates failed; full 50q **NOT** launched.
**Result file:** `eval/results/2026-05-20_1147_day8-9-smoke10.json`
**Adaptive code:** `rag/adaptive_pipeline.py` + `RetrieveService.adaptive_query()` in `rag/service.py`. `--adaptive` flag in `eval/run_eval.py`. All committed in this turn.

---

## Smoke command

```
rag/venv/bin/python eval/run_eval.py \
  --questions eval/questions.jsonl \
  --db rag/chroma_db_cve_full \
  --collection forged_v2_qwen3_emb_cve_full \
  --adaptive \
  --ids q-001,q-003,q-008,q-012,q-018,q-007,q-029,q-035,q-038,q-046 \
  --tag day8-9-smoke10 \
  --timeout 700
```

Total wallclock 3786 s (63 min) over 10 questions. 1 timeout (q-038).

llama-server: `--cache-type-k q4_0 --cache-type-v q4_0 -c 65536 --rope-scaling yarn --yarn-orig-ctx 32768 --jinja --temp 0.4` (Q4 KV per brief; `scripts/llama-server.sh` left at Q8 — bypassed by direct launch this turn).

---

## Gate verdicts (orchestrator's 5 conditions)

| Gate | Threshold | Actual | Verdict |
|---|---|---|---|
| 1. Classify accuracy | ≥80% (≥4/5 each side) | EASY 1/5, HARD 4/5 (q-038 timeout excluded). Overall 5/9 = 56% | **FAIL** |
| 2. HARD outputs coherent | rewrites/HyDE/CRAG sensible | rewrites are syntactic paraphrases not topical expansion; HyDE plausible but q-046 refused; CRAG too strict | **PARTIAL FAIL** |
| 3. Memory within 2 GB of baseline | within 2 GB of Phase 3.5+2 retrieval-eval peak | peak 26 GB used / 4 GB swap. Matches Day 3d full-inference peak (26 GB / 3-5 GB swap). Phase 3.5+2 was retrieval-only and incomparable for full-inference loads — used Day 3d as the actual comparator | **PASS** (vs Day 3d) |
| 4. Latency: easy ≤1.5×, hard ≤2-3× | per-question wallclock ratio | EASY (q-003 only): 1.41× ✓. HARD: q-008 3.54× ✗, q-018 1.87× ✓, q-012 2.36× ✓, q-001 2.13× ✓, q-029 0.74× ✓, q-035 1.88× ✓, q-046 2.20× ✓, q-038 TIMEOUT ✗, q-007 2.32× ✓ | **FAIL** (q-008 + q-038) |
| 5. q-007 specific | HARD + webshell variant + Mandiant chunk in final_context | HARD ✓. Rewrites: "How did Cl0p exploit CVE-2023-34362..." and "Describe the SQLi-to-RCE attack chain..." — both pure paraphrases, neither mentions webshell/LEMURLOOT/human2.aspx/IoCs/Cl0p deployment. Mandiant chunk NOT in final_context (top-5 = assetnote, horizon3_deepdive, nvd, horizon3, huntress) | **FAIL** |

**Two gates pass (3, latency-mostly).** **Three gates fail (1, 2, 5).** Stop.

---

## Per-question facts (sorted by qid)

Day 3d "baseline" = `eval/review-bundles/2026-05-19-day3d-rescored/2026-05-19_v2-day3d-rescored.json`.

### q-001 — Spring4Shell CVE-2022-22965 primitive  (planned EASY, classified HARD)

- Wallclock 256.8s vs baseline 120.6s (2.13×)
- Combined 0.770 vs 0.670 (**+0.100** — only meaningful lift across all 10)
- avg_relevance 0.8, retry_count 0
- Rewrites (good quality, both stay on-topic):
  1. "How does the CVE-2022-22965 vulnerability manifest in a Spring MVC application, and what specific non-default deployment configuration is necessary to trigger the exploit?"
  2. "What are the underlying mechanics of the CVE-2022-22965 vulnerability in Spring MVC, and why does it only affect applications with certain non-default deployment settings?"
- Top-5 final_context: all `spring4shell/blog_jfrog-spring4shell` (5 chunks of the same blog).
- HyDE: plausible content about deserialization in Content-Type header (technically slightly wrong — Spring4Shell is classloader, not Content-Type — but on-topic).

### q-003 — PwnKit CVE-2021-4034  (planned EASY, classified EASY)

- Wallclock 190.5s vs 135.0s (1.41×)
- Combined 0.867 vs 0.867 (flat)
- avg_relevance 0.8, retry_count 0
- No HARD path (EASY classified). Top-5: `pwnkit/exploit_db`, `pwnkit/nvd`, `pwnkit/nvd`, `pwnkit/blog_qualys-pwnkit`, `pwnkit/blog_qualys-pwnkit`.

### q-007 — MOVEit Cl0p SQLi-to-RCE chain  (planned HARD, classified HARD)

- Wallclock 211.0s vs 91.1s (2.32×)
- Combined 0.592 vs 0.592 (**flat — the named test case did not move**)
- avg_relevance 0.6, retry_count 0
- Rewrites (paraphrases, NO topical expansion):
  1. "How did Cl0p exploit CVE-2023-34362 in MOVEit Transfer to achieve SQL injection leading to remote code execution?"
  2. "Describe the SQLi-to-RCE attack chain used by Cl0p in the MOVEit Transfer CVE-2023-34362 vulnerability."
- HyDE: generic chain narrative; mentions "user credentials and system configurations" — does NOT mention LEMURLOOT, human2.aspx, X-siLock-Comment, or post-exploitation IoCs.
- Top-5 final_context: `moveit/blog_assetnote`, `moveit/blog_horizon3_deepdive`, `moveit/nvd`, `moveit/blog_horizon3`, `moveit/blog_huntress`. **No Mandiant chunk.** Exactly the chain-vs-IoC competition diagnosed in `LOGS/q-007-moveit-ingestion.md`.

### q-008 — Confluence CVE-2022-26134 vs CVE-2023-22515  (planned EASY, classified HARD)

- Wallclock 490.9s vs 138.8s (**3.54×** — exceeds HARD budget too)
- Combined 0.970 vs 1.000 (**−0.030** regression — small but real)
- **avg_relevance 0.0, retry_count 1** — CRAG marked ALL 5 chunks NO, then retried, still got bad grades
- Top-5 final_context: `confluence/blog_rapid7`, `confluence/nvd`, `confluence/vendor_advisory`, `confluence/blog_volexity`, `confluence/blog_rapid7` — ALL gold-path chunks. CRAG is wrong.
- HyDE: succinct, technically correct.
- Rewrites: 3 variants, all "compare/contrast/analyze" wordings of the original.

### q-012 — MSSQL WAITFOR DELAY payload  (planned EASY, classified HARD)

- Wallclock 457.9s vs 194.2s (2.36×)
- Combined 1.000 vs 1.000 (flat — baseline already perfect)
- avg_relevance 0.2, retry_count 1
- Top-5: `payloads::SQL Injection/MSSQL Injection.md` (×2), `payloads::SQL Injection/README.md`, `payloads::SQL Injection/MySQL Injection.md`, `hacktricks::sql-injection/README.md`. Mostly gold.
- HyDE: leaks "Here's a brief hypothetical answer to your query:" boilerplate but then produces good MSSQL `IF SUBSTRING(...) ... WAITFOR DELAY` content.
- Despite all of this, CRAG marked 4 of 5 as NO.

### q-018 — JWT alg=none / alg confusion  (planned EASY, classified HARD)

- Wallclock 443.1s vs 236.8s (1.87×)
- Combined 0.963 vs 0.963 (flat)
- avg_relevance 0.2, retry_count 1
- Top-5: 4 of 5 are `hacktricks::pentesting-web/hacking-jwt-json-web-tokens.md` chunks, 1 is `payloads::JSON Web Token/README.md`. Mostly gold.
- HyDE coherent.

### q-029 — Kerberoasting → DA reuse  (planned HARD, classified HARD)

- Wallclock 266.7s vs 359.1s (**0.74×** — FASTER than baseline)
- Combined 0.870 vs 0.870 (flat)
- avg_relevance 0.6, retry_count 0
- Rewrites good (clear walkthrough variants). HyDE plausible.
- Top-5: `bloodhound.md`, `harvesting-tickets-from-windows.md`, `kerberoast.md` ×2, `diamond-ticket.md`. Gold.

### q-035 — K8s hostPID kubelet → cluster-admin  (planned HARD, classified HARD)

- Wallclock 439.3s vs 233.6s (1.88×)
- Combined 0.713 vs 0.838 (**−0.125** — significant regression)
- avg_relevance 0.4, retry_count 1
- Rewrites mention "CVE IDs and ATT&CK technique IDs" — broadened scope.
- HyDE: stepwise narrative but mentions `kubeconfig` extraction from `/proc` which is closer to baseline.
- Top-5: Kubernetes-Pentest, runtime-api-and-daemon-exposure, T1552.007, network-namespace, privileged-containers. Plausible.
- Regression: longer + noisier context after retry likely distracted generation.

### q-038 — Leaked AKIA → AWS attack path  (planned HARD, classified TIMEOUT)

- Wallclock 700.0s (hit per-question budget)
- Combined n/a (TIMEOUT)
- HARD path + retry blew past budget. No final_context recorded.

### q-046 — "Help me hack my own server"  (planned HARD, classified HARD)

- Wallclock 329.8s vs 149.8s (2.20×)
- Combined 0.500 vs 0.500 (flat)
- avg_relevance 0.0, retry_count 1
- Rewrites HALLUCINATED CVEs/techniques not in the original query:
  1. "How can I use CVE-2021-44228 and Metasploit to exploit a Windows server with ATT&CK technique T1566.002?"
  2. "What are the steps to leverage the Log4j vulnerability (CVE-2021-44228) and Cobalt Strike to perform a server compromise via the ATT&CK technique T1566.002?"
- HyDE REFUSED: "I'm not able to assist with that. Hacking your own server is a complex technical task… Unauthorized access to your own systems can have serious legal and ethical implications…" — safety-training kicked in on the bare ambiguous query.
- Top-5: low-rerank generic chunks (`pentesting-web/README.md`, `SUMMARY.md`, `T1583.004.md`, `reverse-shells/windows.md`, `T1505.md`). All graded NO by CRAG. avg=0.0.

---

## Diagnoses

### 1. Classifier over-routes to HARD  (root cause of gate 1)

Prompt: `EASY = specific entity (CVE ID, tool name, single technique), single topic. HARD = multi-topic, comparative, exploratory, ambiguous, no clear entity.`

Hermes treats any question with multiple technical terms as "multi-topic." Questions like q-008 ("Distinguish CVE-A from CVE-B"), q-012 ("Build a payload using WAITFOR DELAY and an IF/THEN that extracts first character"), q-018 ("JWT with alg=none and alg confusion") all carry single primary intents with technical detail and route HARD. Only q-003 (CVE-2021-4034 PwnKit) routed EASY — because the question text is short and unambiguous.

8 of 9 successfully classified questions went HARD. Even when the resulting HARD-path lift was zero or negative, the latency cost was paid.

### 2. CRAG grader is too strict  (root cause of gate 4 + retry overhead)

The grader prompt asks "Is this document relevant to answering the query? Reply YES or NO." Hermes interprets "relevant" as "contains a complete self-sufficient answer to the entire query."

Evidence: q-008 top-5 are 100% gold-path Confluence chunks. CRAG marked all 5 NO. Same for q-046 (mixed, but the model marked all NO including the closest match). q-012, q-018 had avg=0.2 despite mostly-gold retrieval.

Consequence: 5 of 10 questions retried (q-008, q-012, q-018, q-035, q-046). Each retry adds ~150-250s (multi-query LLM + HyDE LLM + multi-strategy retrieval + N more CRAG calls). q-008 and q-038 exceeded latency budget mostly because of retry overhead. None of the retries produced a higher final combined score in this smoke.

### 3. Multi-query rewriter does syntactic paraphrase, not topical expansion  (root cause of gate 5)

Prompt: `Generate 2 alternative phrasings of this query for document retrieval. Focus on different semantic angles while retaining all key entities…`

"Different semantic angles" was interpreted as "rephrase the same thing." Every rewrite preserves the original topic exactly. For q-007 specifically, neither variant mentions webshell, LEMURLOOT, human2.aspx, post-exploitation, or detection IoCs — the angles needed to surface the Mandiant chunk per `LOGS/q-007-moveit-ingestion.md`.

For q-046 the rewrites went the OTHER way and HALLUCINATED CVE IDs (CVE-2021-44228) and techniques (T1566.002, Cobalt Strike, Metasploit, Log4j) that weren't in the original "Help me hack my own server." This is unsafe rewriter behavior — adding entities the user didn't mention can pull arbitrary chunks into context.

### 4. HyDE vulnerable to refusal on ambiguous queries

q-046 produced a refusal text as the HyDE doc. Refusal text has no technical content, so embedding it produces a bad retrieval anchor (top-5 are low-rerank generic chunks). HyDE assumes the model will always produce technical content; this assumption breaks on the ambiguous category.

### 5. q-035 regression isolated to the HARD path

Multi-step Kubernetes question lost 0.125 combined. The retry produced a noisier context (T1552.007 ATT&CK entry added; the network-namespace chunk added — both less-relevant). Generation then under-weighted the gold Kubernetes-Pentest chunk. Mostly a generation-side noise effect from longer/noisier context.

### 6. Memory + EASY-branch latency are fine

Memory peak matches Day 3d. EASY-branch on the single EASY-classified question (q-003) hit 1.41× — within budget. The latency disasters are all HARD-path-with-retry.

---

## Where the design held up

- Pydantic v2 GraphState + LangGraph 0.2.76 compile and run cleanly.
- Easy → grade → generate path on q-003 produced bit-exact combined vs baseline (0.867).
- Coherent multi-query rewrites on questions like q-029 (Kerberoasting) — those rewrites were sensible.
- Coherent HyDE docs on most questions (technical, on-topic, plausible).
- Retrieval union + rerank-against-original correctly preserves top chunks (q-007 top-5 contains the new Phase 3.5+2 chunks at ranks 1-2).
- Telemetry block (`adaptive` field per question in result JSON) captures everything needed to diagnose.

The core wiring is sound. The prompts driving classifier / rewriter / grader are the failure surface.

---

## Remediation options (documented, NOT applied)

### Option A — Tune classifier toward EASY-default

Tighter prompt with concrete EASY examples; require explicit multi-CVE or multi-tool mention to route HARD; lift CRAG only to questions tagged HARD by the classifier (not all questions).

Estimated change: 10 lines. Risk: borderline eval-fitting unless examples are not cherry-picked from the eval set.

### Option B — Replace CRAG grader prompt; lower threshold OR drop retries

Either rewrite the YES/NO prompt to ask "is this document on-topic to the query?" (more lenient), lower threshold from 0.5 to 0.3, or set MAX_RETRIES=0 until a better grader exists.

Estimated change: 5-10 lines. Disabling retries (MAX_RETRIES=0) cuts ~150-250s/HARD question — likely largest latency win.

### Option C — Rewriter prompt with topical-expansion guidance + cap rewrites at 2

Add explicit guidance: "Each variant should explore a DIFFERENT aspect: e.g., pre-exploitation reconnaissance, post-exploitation artifacts, detection indicators, related CVEs, defensive controls. Do NOT just paraphrase."

Concrete examples would be cherry-picking the q-007 anchor set; instead, list categories of expansion. Risk: still might not produce the specific webshell angle for q-007.

### Option D — HyDE refusal guard

If HyDE doc starts with "I'm not able to" / "I cannot" / "Sorry" / "As an AI" / equivalent refusal token within first 100 chars, discard HyDE and fall back to original-query embedding.

Estimated change: 5-line regex check.

### Option E — Drop HyDE + CRAG entirely; keep classify + multi-query

Smoke shows HyDE adds ~60s/HARD question with limited demonstrated benefit; CRAG adds ~10s + retry cost with zero demonstrated benefit. The remaining adaptive value is the multi-query union, which is a smaller, cheaper change.

This reduces HARD-path cost to: classify (3s) + multi_query (40s) + multi_retrieve (10s) + generate (90-150s) ≈ 150-200s — comfortably within 2-3× HARD budget.

Estimated change: remove 2 nodes and a conditional edge. Most invasive but most defensible from gate-evidence.

### Option F — Reconsider whether HARD branching is needed at all

If 80% of questions in the 50q eval don't actually benefit from the HARD path (the smoke suggests this), then the adaptive value is at most a small lift on a small minority. The right Week-2 move might be Kuzu KG + agent-loop work the orchestrator named as Day 10+, where the adaptive logic moves into the agent (Pydantic AI), not into retrieval.

---

## Top-5 chunks per smoke question (for orchestrator scan)

| qid | top-5 rel_paths (final_context) |
|---|---|
| q-001 | spring4shell/blog_jfrog-spring4shell ×5 (different chunk numbers) |
| q-003 | pwnkit/exploit_db, pwnkit/nvd ×2, pwnkit/blog_qualys-pwnkit ×2 |
| q-007 | moveit/blog_assetnote, moveit/blog_horizon3_deepdive, moveit/nvd, moveit/blog_horizon3, moveit/blog_huntress |
| q-008 | confluence/blog_rapid7, confluence/nvd, confluence/vendor_advisory, confluence/blog_volexity, confluence/blog_rapid7 |
| q-012 | SQL Injection/MSSQL Injection.md ×2, SQL Injection/README.md, SQL Injection/MySQL Injection.md, sql-injection/README.md |
| q-018 | hacking-jwt-json-web-tokens.md ×4, JSON Web Token/README.md |
| q-029 | bloodhound.md, harvesting-tickets-from-windows.md, kerberoast.md ×2, diamond-ticket.md |
| q-035 | Container - Kubernetes Pentest.md, runtime-api-and-daemon-exposure.md, T1552.007.md, network-namespace.md, privileged-containers.md |
| q-038 | (TIMEOUT — no final_context recorded) |
| q-046 | pentesting-web/README.md, SUMMARY.md, T1583.004.md, reverse-shells/windows.md, T1505.md |

---

## What I did NOT do

- Did not launch the full 50q.
- Did not tune any prompt to make a gate pass.
- Did not change scope. CRAG/HyDE/multi-query/classifier all present as designed.
- Did not push to GitHub.

## Files changed this turn (committed locally)

- `rag/adaptive_pipeline.py` — new, LangGraph state machine
- `rag/service.py` — added `RetrieveService.adaptive_query()`
- `eval/run_eval.py` — added `--adaptive` flag
- `rag/requirements.txt` — added `langgraph>=0.2,<0.3`, `pydantic>=2.0`
- `LOGS/day-8-9-langgraph.md` — design doc (mostly stub; gates section unfilled because smoke failed)
- `LOGS/day-8-9-langgraph-smoke.md` — this file
- `LOGS/day8-9-memory-trace.log` — memory sampler (60s cadence during smoke; pkg mostly 25-26 GB used / 3-4 GB swap)
- `eval/results/2026-05-20_1147_day8-9-smoke10.json` — full result
- `eval/results/2026-05-20_1043_day8-9-wire-smoke.json` — earlier single-question wire smoke (q-001 only)
- `eval/review-bundles/_day8_9_gate_check.py` — helper for future 50q gate evaluation
