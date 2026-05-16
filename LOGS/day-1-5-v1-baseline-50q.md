# Day 1.5 — 50-question v1 baseline

Dates: 2026-05-15 (kickoff + first hang) → 2026-05-16 (recovery + completion).

## Sequence of events

### Run 1 — 50q baseline (`--think off`, 300 s/q, 2026-05-15 ~16:14)
- Killed previously-hung 5-question smoke had been clean (mean_combined 0.569). 50 real questions written to `eval/questions.jsonl` matching the Day-1 schema.
- Pre-flight: ATT&CK MITRE chunks verified — T-codes appear in both `rel_path` (`enterprise-attack/T1059.001.md`) and `section_path`. Used both `gold_chunk_paths` and `gold_chunk_substrings` with the T-code for q-021..q-028.
- Run kicked off at 16:14.
- Q1–Q14 completed normally (mean ~6 min/q on the v1 stack: ~9 GB Q4_K_M model with only 19/49 layers on the Arc 140V iGPU because Ollama capped the UMA pool at ~6 GB; the rest of the model is in CPU memory).
- Q15 (Twig SSTI) hung. Python eval main thread observed `wait_woken`; no further `/api/generate` calls in `ollama.log` after 16:46:55. iGPU was actually pegged at 99 % the whole time but I read CPU first and called it queue-blockage. Wrong call.

### Hardening pass (2026-05-16 ~09:30, commit `a6a5ef0`)
- Added `concurrent.futures.ThreadPoolExecutor.submit(...).result(timeout=300)` per-question wrapper. On timeout: record null scores, set `status="timeout"`, continue. Worker thread leaks (CPython cannot kill threads from outside).
- Added incremental writes to `eval/results/partial-<tag>.jsonl` with fsync per question — any future hang leaves recoverable state.
- Added `--resume <partial.jsonl>` flag — skip ids already present, fold those records into the final aggregate.
- Added live status line per question: `[q-NNN | category] ok|TIMEOUT combined=X in Ys`.

### Run 2 — 50q baseline restart (`--think off`, 300 s/q, 2026-05-16 ~09:30)
- Q1–Q14 ran clean again. Then Q15 hit the 300 s timeout. Q16, Q17, Q18, Q19 all hit 300 s timeouts back-to-back, all with `answer_chars=0` and `thinking_chars=0`.
- Kept misreading the failure as queue blockage. User pointed out the iGPU was at 99 % the whole time, which was the key signal I had been ignoring.

### Real diagnosis (2026-05-16 ~10:30)
- `rag/service.py`'s `ThinkTagStreamParser` separates streamed text into `<think>` vs answer. With `--think off`, `emit_thinking=False` → every chunk where `in_think=True` is silently dropped (no event yielded).
- DeepSeek-R1 abliterated emits unclosed `<think>` blocks on certain prompts (consistent with llama.cpp #20837 / Ollama #14493, already flagged in BUILD_JOURNAL Chapter 0).
- For Q15 onward, the model was on a `<think>` run with no closing tag. iGPU pumped tokens for 300 s, parser stayed in `in_think=True`, runner silently discarded every token, ANSWER_CHUNK and THINKING never fired (THINKING was suppressed by `emit_thinking=False`), the iterator never reached DONE.
- Worker thread spun forever. Wallclock fired. With `OLLAMA_NUM_PARALLEL=1` the leaked thread held the slot. Q16+ queued behind it and timed out identically.

### Second hardening pass (2026-05-16 ~11:00, commit `3b931fc`)
1. `--think` default flipped to `on`. Stuck-in-think loops now show as accumulating `thinking_chars` instead of silent zero-token timeouts.
2. `PER_QUESTION_TIMEOUT_S` raised 300 → 600 s. Capturing `<think>` roughly doubles the per-question token budget.
3. `_kill_ollama_runner()` fires after every timeout. `pgrep -f 'ollama runner'` + `os.kill SIGKILL`; `ensure_ollama_running` respawns a fresh runner. Subsequent question gets a clean slot.

### Recovery (2026-05-16 ~11:04 → 12:04)
- Trimmed `partial-v1-baseline-50q.jsonl` to keep only Q1–Q14 (14 ok records; dropped 6 zero-token timeout entries).
- Re-launched with `--resume eval/results/partial-v1-baseline-50q.jsonl`.
- Q15 (the previously-cursed Twig SSTI question) completed cleanly at 173 s with `combined=0.667` — definitive confirmation of the diagnosis. The model is generating into `<think>`; with `--think on` the tokens land in `thinking_text` and the stream closes normally.
- Q35 (K8s hostPID multi-step) hit the 600 s ceiling with `ans=0 think=0` — true v1-runtime failure on a heavy chained-reasoning question, not the discarded-token bug. Recovery fired: killed runner, ensure_ollama re-armed, Q36 picked up on a clean slot.
- Q40 (GCP SSRF → metadata → service-account → org admin) — same pattern as Q35, second legitimate timeout, recovery handled cleanly.
- Run completed at 12:04. Exit code 0.

## Final aggregate (`eval/results/2026-05-16_1104_v1-baseline-50q.json`)

| metric | value |
|---|---|
| questions | 50 |
| timeouts | 2 (q-035, q-040) |
| wall_clock (this resume run) | 5595.8 s (~93 min) |
| mean_per_question_s (this resume run) | 155.4 s |
| mean_retrieval_score | 0.654 |
| mean_fact_score | 0.333 |
| mean_hallucination_penalty | 1.000 |
| **mean_combined** | **0.506** |

### Per category (combined)

| category | retrieval | fact | halluc | combined |
|---|---|---|---|---|
| payload-specific | 0.927 | 0.550 | n/a | 0.739 |
| attack-technique | 0.809 | 0.492 | 1.000 | 0.657 |
| ambiguous | 1.000 | 0.133 | n/a | 0.567 |
| multi-step | 0.602 | 0.261 | n/a | 0.431 |
| cve-specific | 0.160 | 0.195 | 1.000 | 0.235 |

`halluc=n/a` in payload-specific / multi-step / ambiguous reflects empty `must_not_hallucinate` lists by design (no specific wrong-answer probes for those categories). Ambiguous `retrieval=1.0` is the known artifact of empty gold lists feeding a `recall=1.0` default in `score.py` (documented in DECISIONS).

### Top 5 worst by combined

| id | combined | note |
|---|---|---|
| q-009 | 0.000 | polkit CVE-2021-3560 — retrieval missed; model answered without grounding |
| q-035 | n/a [TIMEOUT] | K8s hostPID escalation |
| q-040 | n/a [TIMEOUT] | GCP SSRF → metadata → service-account chain |
| q-006 | 0.037 | CitrixBleed CVE-2023-4966 — niche CVE, retrieval thin |
| q-039 | 0.075 | Azure device-code phishing — wrong-grounding facts |

### Compare to Day-1 smoke
```
retrieval  smoke=0.590  latest=0.654  delta=+0.064
fact       smoke=0.333  latest=0.333  delta=-0.001
halluc     smoke=1.000  latest=1.000  delta=+0.000
combined   smoke=0.569  latest=0.506  delta=-0.063
```
Smoke and 50-q baselines are not directly comparable (different questions, different shapes). Per the brief, this is just a sanity check — no zero-delta across categories means the harness is exercising different question profiles, which is what we want.

## Open observations for orchestrator

- **CVE-specific 0.235 is the single largest target for Day 2.** Retrieval is the bottleneck (0.160), not generation — Phase A.5 contextual retrieval will probably move this more than the model swap. Worth watching the CVE-specific combined as the leading indicator after each Day-2 phase.
- **Two true timeouts in 50 questions (4 %)** with `--think on` and 600 s/q. Both are in the multi-step category and both are cloud/K8s-heavy. The v2 plan (Hermes 4 + llama-server Vulkan, `-ngl 99` for full iGPU offload) should pull these under budget on tok/s grounds alone, before any quality lift.
- **Hallucination penalty stayed at 1.0** for all categories that had probes — none of the named-wrong CVE strings (e.g., CVE-2022-22963 in the Spring4Shell answer, CVE-2021-3560 in the PwnKit answer) appeared in any answer without retrieved support. v1 model is sturdy on this axis on a 14B abliterated base.
- **Wall-clock cost of the v1 stack is the real story.** ~93 min for 36 questions on the resume run, ~6 min/q overall when including the original 14. The cost is dominated by 19/49 layers running on CPU because Ollama caps the UMA "GPU" pool at ~6 GB; Day 2's llama-server with `-ngl 99` should triple throughput by forcing all layers onto the iGPU.

## Files

- Final result: `eval/results/2026-05-16_1104_v1-baseline-50q.json` (~240 KB, gitignored).
- Partial JSONL (intermediate state, gitignored): `eval/results/partial-v1-baseline-50q.jsonl`.
- This log: `LOGS/day-1-5-v1-baseline-50q.md`.

## Commits today

```
3b931fc  Eval: default --think on, 600s/q timeout, kill ollama runner on timeout
a6a5ef0  Harden eval runner: per-question timeout + incremental writes + resume
```

The next commit (Phase A baseline summary) lands on top of this log.
