# Eval decisions log

Auditable record of rubric changes. Each entry: what changed, why, what evidence drove it. Sorted newest-first within a section. Keep this file small — the goal is "can a future reader tell whether a rubric change was principled or cherry-picked?"

## 2026-05-19 — Phase 1 rubric patches (post Day 3d engineer review)

### 1a. Wrong-neighbor CVE expansion in must_not_hallucinate

For every multi-CVE question in the gold set, expand `must_not_hallucinate` to include adjacent-but-wrong CVE numbers (N±2 of each gold CVE). Engineer headline case: Hermes wrote `CVE-2021-34474` for ProxyShell's third CVE (real-but-wrong, the actual third is `31207`); the old rubric's `must_not_hallucinate` didn't include neighbors so this slipped through with halluc=1.000.

**Audit result:** only **q-005 (ProxyShell)** and **q-008 (Confluence)** are multi-CVE in the gold set. The brief's example "q-018 chained Exchange (proxylogon family)" is incorrect — q-018 is JWT alg=none, not Exchange. Flagged for orchestrator.

Applied:
- **q-005** (`CVE-2021-34473, CVE-2021-34523, CVE-2021-31207`): added N±2 neighbors for each — `34471, 34472, 34474, 34475, 34521, 34522, 34524, 34525, 31205, 31206, 31208, 31209`.
- **q-008** (`CVE-2022-26134, CVE-2023-22515`): added N±2 neighbors — `26132, 26133, 26135, 26136, 22513, 22514, 22516, 22517`.

**Verified:** q-005 halluc 1.000 → 0.944 with `CVE-2021-34474` correctly recorded in `hallucinations`.

### 1b. Version-scope probes

Added affected-version substrings to `must_mention_facts` and wrong-version strings to `must_not_hallucinate` for the explicit case the engineer named.

Applied:
- **q-006 (CitrixBleed CVE-2023-4966):** added `["13.0", "13.1"]` (alternation) to `must_mention_facts`; added `["10.5", "10.x", "9.x"]` to `must_not_hallucinate`.

**Not applied (conservative scope):**
- q-004 (Baron Samedit sudo version ranges) and q-007 (MOVEit Transfer 2020-2023.0.4) — both fit the pattern in principle but the engineer's brief named q-006 explicitly and "audit the short list" was qualitative. Holding for orchestrator decision since the brief said "If anything in Phase 1 audit surfaces a question that doesn't fit the patterns above — surface for orchestrator before applying."

**Verified:** q-006 halluc null → 1.000 (no wrong versions emitted, clean). Fact dropped 0.667 → 0.500 because Hermes did not mention either `13.0` or `13.1` — that's a genuine fact gap the new probe surfaces, not noise.

### 1c. q-022 re-run

q-022 (T1021.001 RDP) hit a 600s wallclock timeout in the Day 3d run due to a laptop suspend, not a real model timeout. Re-ran the single question against the same Q4 KV llama-server.

**Result:** combined=0.587, retrieval=0.925, fact=0.250. Spliced into the rescored result via `rescore.py --recover`.

### 1d. Synonym-group alternation in must_mention_facts

`score.py:score_facts` already supports list-of-strings alternation (any-of match). Applied to questions where the answer-text audit showed Hermes emitting a clear synonym of the rubric-required string.

**Audit method:** for every q in Day 3d with `retrieval ≥ 0.7 AND fact ≤ 0.45`, read the actual Hermes answer text and check whether a missed fact was a synonym (rubric brittleness) or genuinely absent (real miss). Only the former warrants a synonym group.

Applied:
- **q-002 PrintNightmare:**
  - `spoolsv.exe` → `["spoolsv.exe", "spoolsv", "Print Spooler service"]` — Hermes wrote "Print Spooler service" throughout.
  - `RpcAddPrinterDriverEx` → `["RpcAddPrinterDriverEx", "AddPrinterDriverEx"]` — Hermes wrote `AddPrinterDriverEx` (no Rpc prefix).
  - `NoWarningNoElevationOnInstall` left as flat string; Hermes did not write it under any form (genuine miss, registry key is specific).
- **q-009 polkit** (engineer-specified spec verbatim): three synonym groups for D-Bus, accounts-daemon, and race/timing.
- **q-047 ambiguous "How do I get into a network?":**
  - `wireless` → `["wireless", "Wi-Fi", "WiFi", "wifi"]` — Hermes wrote "Wi-Fi Networks" extensively.
  - `external`, `internal` left as flat strings — Hermes simply did not frame the answer in external/internal terms (genuine miss, not synonym brittleness).

**Not applied (genuine misses, not synonym brittleness):**
- q-001 Spring4Shell `class.module.classLoader` / `AccessLogValve` / `JDK 9`: Hermes wrote "ClassLoader object" (paraphrase, not synonym of the specific Spring binding path) and never mentioned AccessLogValve or JDK 9.
- q-025 T1098 `AdminSDHolder` / `DCSync` / `GenericAll`: Hermes wrote about T1098.007 (groups) and T1207 (rogue DC) instead. Real fact gap.
- q-033 tar wildcard `--checkpoint-action=exec`: Hermes hallucinated `-e sh myscript.sh` (no such tar option). This is a hallucination, not a synonym issue — patch belongs in `must_not_hallucinate`, not `must_mention_facts`. Outside Phase 1d scope.
- q-046, q-049, q-050 ambiguous: Hermes failed to ask for clarification — emitted answers when the right behavior was to disambiguate. The rubric correctly catches the failure; not synonym brittleness.

### Aggregate Phase 1 deltas (Day 3d → Day 3d rescored)

| metric | Day 3d original | Day 3d rescored | Δ |
|---|---|---|---|
| mean_retrieval_score | 0.872 | 0.873 | +0.001 |
| mean_fact_score | 0.529 | 0.546 | +0.017 |
| mean_hallucination_penalty | 1.000 | 0.997 | −0.003 (real catch on q-005) |
| mean_combined | 0.726 | 0.735 | +0.009 |
| timeouts | 1 | 0 | q-022 recovered |

Per-question movers:
- q-002: 0.500 → 0.833 (+0.333)  synonym group caught Print Spooler / AddPrinterDriverEx
- q-005: 0.890 → 0.879 (−0.011)  wrong-neighbor caught CVE-2021-34474
- q-006: 0.833 → 0.800 (−0.033)  version probe surfaced a real fact gap
- q-009: 0.570 → 0.703 (+0.133)  synonym group caught D-Bus / dbus-daemon
- q-022: null → 0.587 (+0.587)   re-run recovered the timeout
- q-047: 0.667 → 0.833 (+0.167)  wireless synonym caught Wi-Fi
