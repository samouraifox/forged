# Phase 3.5+2 — q-007 MOVEit operator-anchor ingestion

**Date:** 2026-05-19
**Predecessor:** Phase 3.5+1 diagnosis at `LOGS/q-007-moveit-diagnosis.md`
**Outcome:** Partial success. Corpus expansion landed correctly; q-007 retrieval flat due to a query–rubric semantic mismatch surfaced during evaluation.

---

## Sources fetched

| File | Source URL | Net adds |
|---|---|---|
| `data/cve_ingest/moveit/blog_horizon3_deepdive.md` | horizon3.ai/attack-research/.../moveit-transfer-cve-2023-34362-deep-dive... | New |
| `data/cve_ingest/moveit/blog_assetnote.md` | assetnote.io/resources/research/moveit-transfer-rce-part-two-cve-2023-34362 | New |

MOVEit corpus grew 235 → 609 lines (~2.6× expansion). Chroma collection grew 14,417 → 14,425 (+8 chunks net after rebuild).

### Brief vs reality on sources

- Brief named **watchTowr** as the primary target. **watchTowr has no CVE-2023-34362 writeup** — only the CVE-2024-5806 SFTP auth-bypass writeup (already in the corpus as `moveit-authbypass-2024/blog_watchtowr`).
- The canonical operator-grade sources for CVE-2023-34362 are **Horizon3.ai** (deep dive with handler chain + IoCs) and **AssetNote** (technical reverse-engineering with function table + code).

## Anchors — brief vs ground truth

Cross-checked against Mandiant, Horizon3, AssetNote, Unit42, Talos, CISA #StopRansomware, and Anomali writeups.

| Brief anchor | Real? | Decision |
|---|---|---|
| `human2.aspx` | ✓ | already in `blog_huntress`, `blog_mandiant`; preserved |
| `LEMURLOOT` | ✓ | already in `blog_mandiant`; now also `blog_assetnote` |
| `X-siLock-Comment` | ✓ | already in `blog_mandiant`; now also `blog_assetnote` |
| `X-siLock-Transaction` | ✓ | NEW: in `blog_horizon3_deepdive`, `blog_assetnote` |
| `SaveFile` | ✗ — not in any documented writeup | DROPPED with orchestrator approval |
| `FolderEvalAction` | ✗ — not in any documented writeup; closest real handler is `FolderAddByPath` | DROPPED with orchestrator approval |

Acceptance target adjusted from "≥4 of 6 anchors" to "≥4 of 4 real anchors" with orchestrator decision logged via AskUserQuestion.

## Step 2 smoke — anchor coverage in saved markdown

```
human2.aspx           in blog_huntress, blog_assetnote, blog_mandiant       (3 files)
LEMURLOOT             in blog_assetnote, blog_mandiant                       (2 files)
X-siLock-Comment      in blog_mandiant, blog_assetnote                       (2 files)
X-siLock-Transaction  in blog_assetnote, blog_horizon3_deepdive              (2 files) — NEW
```

Bonus operator strings now in the corpus: `machine2.aspx`, `SetAllSessionVarsFromHeaders`, `UserGetUsersWithEmailAddress`, `BinaryFormatter`, `DeserializeFileUploadStream`, `action_m2`, `CrackInput`, `FolderAddByPath`, `MyPkgSelfProvisionedRecips`, `fileuploadinfo`.

## Step 3 — collection rebuild

- Source: `BASELINE_COLLECTION="forged_v2_qwen3_emb_context_partial_1421"` (14,308 chunks)
- Plan: 117 CVE chunks across 26 folders (19 moveit, +5 vs prior 14)
- Result: 14,425 total chunks
- BM25 index regenerated; cosine HNSW space preserved

## Step 4 — retrieval-only eval

Result file: `eval/results/2026-05-19_day3.5+2-moveit-retrieval.json`

### Aggregate (vs 2026-05-18 day3.5 retrieval baseline)

```
mean_retrieval_score:  0.873 → 0.873   (delta = +0.000)
mean_combined:         0.873 → 0.873   (delta = +0.000)
```

### q-007 (the target question)

```
retrieval_score    : 0.850 → 0.850     (unchanged)
path_recall        : 1.000 → 1.000     (path keywords already matched)
substring_recall   : 0.500 → 0.500     (2 of 4 — moveit + CVE-2023-34362 match;
                                        human2.aspx + LEMURLOOT still don't surface)
```

### Per-question regression check

```
regressions (≥ 0.01):  0
gains (≥ 0.01):        0
```

Other 49 questions: bit-exact on retrieval. The corpus expansion did not perturb any non-MOVEit retrieval.

## Anchor coverage in q-007 top-5 (the acceptance gate)

```
human2.aspx           in top-5: 0 chunks      ✗
LEMURLOOT             in top-5: 0 chunks      ✗
X-siLock-Comment      in top-5: 0 chunks      ✗
X-siLock-Transaction  in top-5: 0 chunks      ✗
```

**0 of 4 real anchors in top-5.** Acceptance gate (≥4 of 4) failed.

## Top-30 first-appearance ranks

```
human2.aspx           NOT FOUND in top-30
LEMURLOOT             NOT FOUND in top-30
X-siLock-Comment      NOT FOUND in top-30
X-siLock-Transaction  rank 15  (moveit/blog_assetnote, header smuggling section)
```

The Mandiant chunk that contains human2.aspx + LEMURLOOT + X-siLock-Comment together (was rank 11 in Phase 2 diagnosis) is now ranked **deeper than 30** because the new chain-content chunks displaced it.

## Diagnosis — query–rubric semantic mismatch

The q-007 question wording — *"what's the SQLi-to-RCE chain Cl0p used?"* — semantically anchors the reranker on chain content: `BinaryFormatter` deserialization, `DeserializeFileUploadStream`, `MsgPostForGuest`, `SetAllSessionVarsFromHeaders`, the SQL injection sink. These are the chain.

The rubric anchors (`LEMURLOOT`, `human2.aspx`, `X-siLock-Comment`) are post-exploitation webshell artifacts. The webshell is *deployed by* the chain but isn't *part of* the chain — they're conceptually distinct.

Probe with operator-flavored wording confirms the corpus is intact:

```
Query: "LEMURLOOT webshell human2.aspx X-siLock-Comment Cl0p exploitation chain"
  human2.aspx              rank 1 — moveit/blog_mandiant
  LEMURLOOT                rank 1 — moveit/blog_mandiant
  X-siLock-Comment         rank 1 — moveit/blog_mandiant
  X-siLock-Transaction     rank 12 — moveit/blog_assetnote
```

When the query mentions the webshell explicitly, every anchor surfaces at rank 1 of the Mandiant chunk. The corpus is fine. The query is the issue.

## Net effect on q-007

The new sources (assetnote, horizon3_deepdive) landed at ranks 1, 2, 5 — exactly where Phase 2 diagnosis predicted they should. But they're **chain-relevant** content, not **IoC-relevant** content. They competed with and displaced the Mandiant chunk that previously held the IoC anchors at rank 9.

In retrieval terms: q-007's `path_recall=1.0` was already saturated. `substring_recall=0.500` is the ceiling under the current query/rubric pairing — substrings 1-2 (`moveit`, `CVE-2023-34362`) match in path, substrings 3-4 (`human2.aspx`, `LEMURLOOT`) don't surface for this wording at top-5.

## Decision (orchestrator)

Per `AskUserQuestion` 2026-05-19: **accept partial success, document, move on.**

Rationale:
- Corpus is now genuinely richer with operator-grade content
- Other questions hitting the corpus (multi-step, ambiguous, related CVE-specific) may benefit later under adaptive RAG
- The q-007 misalignment is real but defers to Week 2 (LangGraph adaptive RAG can query-rewrite to operator wording before retrieval)
- No regression elsewhere — corpus expansion is net-neutral or positive corpus-wide, just doesn't lift this specific question on this specific wording

## Open items for Week 2

1. Query rewriting in the adaptive RAG layer: for cve-specific questions, expand the user query with "webshell", "IoC", "deployment", "post-exploitation" tokens before retrieval to surface IoC chunks alongside chain chunks.
2. Consider raising top-k for cve-specific to 10 (Phase 2 Option 1, deferred again) — would have surfaced the Mandiant chunk pre-expansion. With the new expansion it would surface Mandiant at rank 11, so still might not reach a top-10 cutoff. Top-15 would.
3. The Mandiant chunk merging IoCs is operationally the highest-value chunk for q-007. Consider chunk metadata boosting (e.g., source_type weight in BM25) for IoC-bearing chunks.

## Files committed in this phase

- `data/cve_ingest/moveit/blog_horizon3_deepdive.md` (212 lines)
- `data/cve_ingest/moveit/blog_assetnote.md` (162 lines)
- `rag/chroma_db_cve_full/` rebuilt (14,425 chunks) — gitignored, regenerable
- `eval/review-bundles/2026-05-19-q007-moveit-ingestion/` bundle
- `LOGS/q-007-moveit-ingestion.md` (this file)
