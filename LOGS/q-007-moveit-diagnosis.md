# q-007 MOVEit — corpus-vs-generation diagnosis

**Date:** 2026-05-19
**Question:** "MOVEit Transfer CVE-2023-34362 — what's the SQLi-to-RCE chain Cl0p used?"
**Day 3d score:** retrieval=0.850, fact=0.333, combined=0.592

## Verdict: BRANCH B (anchors not in top-5 retrieved) — but root cause is retrieval ranking, not corpus absence

The brief defines the branches as a binary on the top-k retrieved chunks. By that definition this is Branch B: none of the operator anchors appear in q-007's top-5. But the corpus actually contains them — they just rank too low to surface at production top-k=5.

## Evidence

### 1. Top-5 retrieved chunks for q-007 (production result)

| # | rel_path | size |
|---|---|---|
| 1 | moveit/nvd | 549 chars |
| 2 | moveit/blog_horizon3 | 511 |
| 3 | moveit/nvd | 397 |
| 4 | moveit/blog_huntress | 488 |
| 5 | moveit/blog_horizon3 | 583 |

Total context: ~2.5 KB of high-level CVE description + Horizon3/Huntress excerpts.

### 2. Anchor presence in top-5

| anchor | [1] | [2] | [3] | [4] | [5] |
|---|---|---|---|---|---|
| `human2.aspx`       | . | . | . | . | . |
| `LEMURLOOT`         | . | . | . | . | . |
| `X-siLock-Comment`  | . | . | . | . | . |
| `X-siLock-Transaction` | . | . | . | . | . |
| `SaveFile`          | . | . | . | . | . |
| `Cl0p`              | . | . | . | . | . |
| `moveitisapi.dll`   | . | . | . | Y | . |
| `SQL injection`     | . | Y | . | Y | Y |
| `deserialization`   | . | . | . | . | Y |

Only orientation-level strings (`SQL injection`, `deserialization`, `moveitisapi.dll`) are in the top-5. Every IoC/payload-grade string is absent.

### 3. Corpus-wide anchor presence (14 MOVEit chunks, 7,692 chars total)

| anchor | corpus hits |
|---|---|
| `human2.aspx`       | 4/14 |
| `LEMURLOOT`         | 3/14 |
| `X-siLock-Comment`  | 2/14 |
| `moveitisapi.dll`   | 2/14 |
| `X-siLock-Transaction` | 0/14 |
| `SaveFile`          | 0/14 |
| `FolderEvalAction`  | 0/14 |
| `Cl0p`              | 0/14 |

Mixed picture. `human2.aspx` and `LEMURLOOT` are present but underrepresented. The deeper deserialization-gadget anchors (`SaveFile`, `FolderEvalAction`, `X-siLock-Transaction`) are missing entirely.

### 4. Where do the anchor-bearing chunks rank?

Probed the retriever with `topk=20`:

| rank | rerank | rel_path | anchors |
|---|---|---|---|
| 1-8 | 0.987-1.000 | nvd / horizon3 / huntress / watchtowr / followup | none |
| **9** | **0.977** | moveit/blog_huntress | **human2.aspx** |
| **10** | **0.924** | moveit/blog_huntress | **human2.aspx** |

First `human2.aspx`-bearing chunk is at **rank 9**. Production top-k=5 cuts it off. The reranker treats the high-level descriptions (rank 1-8) as nearly equivalent matches (rerank=0.987-1.000) to the operator detail (rank 9, rerank=0.977). The gap is tight (~0.02) but consistent.

`LEMURLOOT` and `X-siLock-Comment`-bearing chunks rank even deeper — none appeared in the top-10 probe.

### 5. Hermes's answer text (full)

> The SQL injection-to-RCE chain used by Cl0p in exploiting CVE-2023-34362 involves the following steps:
> 1. SQL Injection: extract a sysadmin access token from the MOVEit Transfer database
> 2. Deserialization: trigger a deserialization vulnerability
> 3. Remote Code Execution: arbitrary code execution

Three correct high-level steps, no operational specifics. Mirrors the retrieved context exactly — no prior-knowledge fill-in.

## Why fact_score=0.333

`must_mention_facts = ["SQL injection", "LEMURLOOT", "human2.aspx"]`. Hermes hit `SQL injection` only. `LEMURLOOT` and `human2.aspx` were never in his context window.

## Proposed fixes (HOLD for orchestrator decision)

### Option 1 — cheap: raise top-k for cve-specific to 10

The first `human2.aspx`-bearing chunk is at rank 9. Raising top-k from 5 to 10 in cve-specific would surface it.

- Pros: zero ingestion work, ~2× context length within Hermes's YaRN budget
- Cons: more competing chunks in context can dilute attention; the rest of the corpus also gets wider top-k
- Expected fact_score lift: q-007 from 0.333 → 0.667 (catches `human2.aspx`)
- Estimated effort: 1-line config change

### Option 2 — robust: ingest the watchTowr "MOVEit Transfer SQL Injection to RCE" writeup

The current MOVEit corpus is 7,692 chars across 14 chunks. That's thin. The watchTowr writeup is operator-grade and contains every anchor the rubric expects, plus the deserialization-gadget detail (`SaveFile`, `FolderEvalAction`, `X-siLock-Transaction`) that's missing entirely from the corpus today.

- Pros: closes the underlying corpus gap; same canonical-ingest pattern as Phase 3.5
- Cons: net-new corpus content; needs greenlight under the same "expanded corpus" decision rule as Phase 3.5
- Expected fact_score lift: q-007 from 0.333 → ~0.85+ (catches `human2.aspx`, `LEMURLOOT`, plus surfaces ProxyShell-grade detail for the underlying chain)
- Estimated effort: ~30 min ingestion + verify with smoke
- Proposed sources (in priority order):
  1. **watchTowr Labs — MOVEit Transfer SQL Injection to RCE** (canonical operator writeup)
  2. **Mandiant — MOVEit / LEMURLOOT** (already 3 chunks in corpus; expand)
  3. **Microsoft Threat Intelligence — Cl0p ransomware affiliate MOVEit campaign**

Wayback Machine snapshots if any live URL has been pulled.

### Option 3 — combined: do both

Best-effort coverage. ~1 hour total.

## Recommendation

Option 2 (ingest watchTowr). Reasoning:

- Option 1 papers over a real corpus-density gap. Raising top-k is a global setting; it would inflate context for every cve-specific question even where the top-5 is fine.
- Option 2 fixes the root cause and is consistent with how Phase 3.5 closed the path_recall=0 gap (canonical-source ingestion).
- The MOVEit corpus is the thinnest in the v2 set (7.6 KB total). Even questions adjacent to q-007 would benefit.

## What I am NOT doing

Holding here for orchestrator decision per brief. No corpus expansion or top-k changes applied.
