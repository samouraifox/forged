# eval/ — forged evaluation harness

A small, deterministic harness for scoring the retrieval + generation stack against a question corpus with gold-chunk labels. Every change to the stack is gated on this number moving the right way; nothing ships unmeasured.

## Files

| File | Purpose |
|---|---|
| `run_eval.py` | Main runner. Loads questions, drives them through `RetrieveService`, scores, writes a result JSON. |
| `score.py` | Pure scoring functions, importable. |
| `compare.py` | Diff two result files. |
| `schema.md` | Documentation of the `questions.jsonl` schema. |
| `rubric.md` | What the three sub-scores mean and how to read a result. |
| `questions.jsonl` | The eval corpus. Five example/smoke questions ship; the orchestrator adds the real 50 separately. |
| `results/` | Output directory. Gitignored — result JSONs are regenerable and large. |

## Quickstart

From the repo root, on a working v1 stack (Ollama running with `hacker-guide` alias built, `rag/chroma_db` populated, `rag/venv/` present):

```bash
# Smoke run against the 5 example questions
python eval/run_eval.py --include-examples --tag smoke

# Real baseline against whatever real questions live in questions.jsonl
python eval/run_eval.py --tag baseline

# Compare two runs
python eval/compare.py eval/results/<earlier>.json eval/results/<later>.json
```

`run_eval.py` auto-re-execs itself under `rag/venv/bin/python` so you don't have to think about which Python you're using — but it does need `rag/venv/` to exist.

## Runner flags

| Flag | Default | Meaning |
|---|---|---|
| `--questions` | `eval/questions.jsonl` | Path to question corpus. |
| `--topk` | `5` | Top-k after reranking. |
| `--rag` | `on` | `on`/`off`. Turns retrieval off entirely (compare ungrounded baseline). |
| `--think` | `off` | `on`/`off`. Native `<think>` toggle on the v1 model. Off by default — faster. |
| `--limit` | (none) | Cap question count. Useful for fast iteration. |
| `--tag` | `baseline` | String embedded in the result filename. Use to tag what stack you were measuring. |
| `--include-examples` | false | Include the 5 smoke questions (`is_example: true`). Default skips them. |
| `--db` | `rag/chroma_db` | Path to the Chroma DB. |

## Output

A result file lands at `eval/results/YYYY-MM-DD_HHMM_<tag>.json`, structured as:

```jsonc
{
  "tag": "smoke",
  "timestamp_utc": "...",
  "model": "DeepSeek-R1 abliterated",   // v1 stack model display name
  "config": { "topk": 5, "rag": true, "think": false, ... },
  "question_count": 5,
  "total_wall_clock_s": 145.3,
  "mean_per_question_s": 29.0,
  "aggregate": {
    "mean_retrieval_score": 0.62,
    "mean_fact_score": 0.40,
    "mean_hallucination_penalty": 0.93,
    "mean_combined": 0.59
  },
  "aggregate_by_category": { "cve-specific": { ... }, "payload-specific": { ... }, ... },
  "per_question": [
    {
      "id": "q-001",
      "category": "cve-specific",
      "question": "...",
      "retrieved_chunks": [ {rel_path, source, section_path, rerank, rrf, ...}, ... ],
      "answer_text": "...",
      "thinking_text": "...",
      "score": { "retrieval_score": 0.7, "fact_score": 1.0, "hallucination_penalty": 1.0, "hallucinations": [], "combined": 0.88 }
    },
    ...
  ]
}
```

`compare.py` prints aggregate deltas, per-category deltas, and per-question changes ≥ 0.10 combined.

## Adding new questions

1. Read `schema.md` for the field semantics.
2. Add one line per question to `questions.jsonl`. Don't reuse `id`s.
3. For real (non-example) questions, leave `is_example` off or set it to `false`.
4. Re-run with `--tag <descriptive>` so the result file is searchable later.

Five categories are defined: `cve-specific`, `payload-specific`, `attack-technique`, `multi-step`, `ambiguous`. The runner doesn't validate the category string — keep typos out of `questions.jsonl` so aggregate_by_category stays clean.

## Scoring at a glance

See `rubric.md` for the full version. Short form:

- `retrieval_score = 0.7 * path_recall + 0.3 * substring_recall`
- `fact_score = matched must_mention_facts / total`
- `hallucination_penalty = 1.0 - (hallucinations / len(must_not_hallucinate))`, where "hallucination" means the forbidden string is in the answer but NOT in retrieved context.
- `combined = 0.4 * retrieval + 0.4 * fact + 0.2 * hallucination`, with weight renormalization when any sub-score is null (empty fact list or empty hallucination list).

## What this harness deliberately does NOT do

- No LLM-as-judge scoring. The whole point is to be cheap, deterministic, and reproducible. LLM-judge layers can be added later as a fourth optional score — they do not gate the existing three.
- No retry-on-flaky. Each question is run exactly once per invocation. Run twice and compare if you suspect noise.
- No partial credit on substring matches. A required fact is either present or not.

## Operational notes

- The runner calls `RetrieveService.retrieve_top_hits` (a strictly-additive method on the service) to capture the raw hit list, then calls `stream_query` for the answer. Retrieval runs twice per question, but the cost is milliseconds and keeps the harness from depending on TUI-specific event shapes.
- Result files are gitignored. The aggregate metrics are summarized in commit messages instead.
- The harness uses whatever model alias `rag.service.LLM_MODEL` points to (currently `hacker-guide` on the v1 stack). When v2 swaps the model, update the alias once and the eval picks it up.
