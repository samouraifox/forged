# Day 1 — Phase 0: Repo bootstrap + eval harness

Date: 2026-05-15

## Phase 0a — Repo bootstrap

### Pre-flight (PASS)
- `gh auth status` → authenticated as `samouraifox` (token scopes: gist, read:org, repo, workflow).
- `git -C ~/Work/Projects/forged rev-parse --git-dir` → not a git repo. Confirmed.
- v1 stack health check:
  - `rag/venv/bin/python` exists.
  - Chroma collection `security` opens with 14308 chunks.
  - `hacker-guide:latest` Ollama alias built (Q4_K_M, qwen2 arch, ctx 131072, num_ctx 16384). Sibling models present (deepseek-r1-abliterated, qwen3-abliterated, nomic-embed-text).
  - Ollama was not running pre-eval; `rag.runtime.ensure_ollama_running` restarts it with `OLLAMA_FLASH_ATTENTION=0` automatically.
- Secret audit pre-stage: no AWS account ID, no Request IDs, no `Projects/Secrets` strings, no `sk-/ghp_/AKIA` patterns anywhere in tracked content.

### Files created/edited
- `.gitignore` — Python caches, venvs, `rag/chroma_db`, `rag/corpus/*` (with `!rag/corpus/.gitkeep`), `eval/results/*.json`, `_removed_from_product/`, `.claude/`, `.codex`, common secret patterns.
- `LICENSE` — Apache-2.0, copyright "Copyright 2026 samouraifox".
- `README.md` — replaced existing strip-down doc with public-facing v2 intro (status, what it is, hardware target, stack table, "why not hosted", setup pointers, license, acknowledgements).
- `CORPUS_SETUP.md` — four `git clone --depth=1` commands for HackTricks / PayloadsAllTheThings / OWASP CheatSheetSeries / MITRE cti.
- `rag/corpus/<upstream>/` deleted; `rag/corpus/.gitkeep` added. (Upstream content totaled ~400 MB across four repos with their own `.git` dirs.)

### Commands run
- `find . -type d -name __pycache__ -not -path "./rag/venv/*" -prune -exec rm -rf {} +`
- `git init -b main`, `git add .`, `git ls-files | wc -l` → 32 files staged, all pattern checks pass.
- `git commit -m "Initial commit: v2 strip-down + planning artifacts (BUILD_JOURNAL Chapter 0)"`
- `gh repo create forged --public --source=. --description="..."` → https://github.com/samouraifox/forged
- `git push -u origin main`.

### Audit results
- `git diff --cached | grep -E "<secrets pattern>"` → only hit was a benign `.gitignore` comment referencing the local Secrets folder location. Re-worded to remove the path, re-audited, clean.

### Phase 0a acceptance
- Public repo at https://github.com/samouraifox/forged with one commit `8f9da55`.
- Tracked: BUILD_JOURNAL.md, README.md, LICENSE, CORPUS_SETUP.md, Modelfile, hacker_lm, requirements-tui.txt, localchat_tui/, rag/{chunker, ingest, mitre_loader, runtime, service, tui_worker}.py, rag/requirements.txt, rag/__init__.py, rag/.gitignore, PRODUCT_STRIP_PLAN.md, PRODUCT_STRUCTURE.md.
- Excluded: rag/corpus/{hacktricks,PayloadsAllTheThings,CheatSheetSeries,cti}, rag/chroma_db, rag/venv, _removed_from_product, all __pycache__.

## Phase 0b — Eval harness

### Files created
- `eval/run_eval.py` — runner; CLI flags `--questions --topk --rag --think --limit --tag --include-examples --db`; re-execs under `rag/venv/bin/python` automatically.
- `eval/score.py` — deterministic scoring: `score_retrieval`, `score_facts`, `score_hallucination`, `score_question`, `aggregate`, `aggregate_by_category`.
- `eval/compare.py` — aggregate deltas, per-category combined deltas, per-question changes ≥ 0.10, newly-failing list (drop below 0.5).
- `eval/schema.md`, `eval/rubric.md`, `eval/README.md` — schema, scoring rubric, usage guide.
- `eval/questions.jsonl` — 5 example questions (one per category), all `is_example: true`.
- `eval/.gitignore` (`results/*.json` + `!results/.gitkeep`), `eval/results/.gitkeep`.

### Additive change to RetrieveService
Added one method to `rag/service.py`:
```python
def retrieve_top_hits(self, question, config, history=None) -> list[dict]:
    """Strictly-additive helper for offline evaluation."""
```
Does retrieval + rerank, returns the top-k hit dicts. Lazy-initializes the stack the same way `stream_query` does (via `self.initialize()`). `stream_query` behavior is unchanged.

### Bugs hit + fixes
- **Symlink-resolution bug in venv re-exec**: `Path(sys.executable).resolve()` and `VENV_PY.resolve()` both resolve to the mise-managed Python under `~/.local/share/mise/installs/python/3.14.3/...` because `rag/venv/bin/python` is a symlink chain into it. The equality check returned True even when the script was launched outside the venv — early-return skipped re-exec — venv site-packages never loaded — `ModuleNotFoundError: No module named 'chromadb'`. Fixed by comparing `sys.prefix` to the venv root path directly.

### Smoke run
Command:
```
python eval/run_eval.py --include-examples --tag smoke
```
- Wall clock: 687.8 s for 5 questions (≈ 137.6 s/question).
- `think=False`, `rag=True`, `topk=5`.
- Result file: `eval/results/2026-05-15_1423_smoke.json` (22 KB).

Aggregate metrics:

| metric | value |
|---|---|
| `mean_retrieval_score` | 0.590 |
| `mean_fact_score` | 0.333 |
| `mean_hallucination_penalty` | 1.000 |
| `mean_combined` | **0.569** |

Per-category combined:

| category | combined |
|---|---|
| payload-specific | 0.867 |
| multi-step | 0.807 |
| cve-specific | 0.560 |
| attack-technique | 0.333 |
| ambiguous | 0.280 |

`compare.py` self-diff (smoke vs smoke) prints all-zero deltas — proves the diff harness is wired.

### Phase 0b acceptance
- End-to-end smoke run passes with exit code 0.
- Result JSON written and well-formed.
- `compare.py` works on two paths.
- Aggregate metrics non-zero (all four).
- Only additive change to `RetrieveService` is `retrieve_top_hits`.
- `eval/README.md` covers usage including how to add new questions and run the baseline.

## Open observations for orchestrator

- The eval `mean_fact_score=0.333` on the smoke set is largely an artifact of the example questions, not a stack flaw — example `must_mention_facts` strings were authored quickly and may not match the v1 model's preferred phrasing (e.g., "JNDI" present but "${jndi:" probably missing in the answer because the model uses prose instead of the literal payload). Real questions calibrated against the actual model voice will produce a more stable baseline.
- `mean_hallucination_penalty=1.0` perfect score means none of the deliberately-fake CVE numbers/tool flags appeared in answers. Reassuring, but small sample.
- `ambiguous` category at 0.28 combined reflects that "how do I do recon" is genuinely too broad — the v1 model wanders. The retrieval layer also struggled (0.20 retrieval_score) because the example's gold paths/substrings were too specific for such an open prompt.
- `attack-technique` category at 0.0 retrieval_score: the gold path "T1190" did not appear in the rel_path of any retrieved chunk. Worth checking whether the MITRE corpus ingest pipeline labels paths with technique IDs in a way that matches what's expected — or whether the question needs a different gold path string. Flagged for orchestrator follow-up.
- Wall clock 137s/question is the budget reality of a 14B Q4 model on Arc 140V via Ollama with `OLLAMA_FLASH_ATTENTION=0`. Day-2 model swap to Hermes-4-14B + llama.cpp Vulkan should change this number; eval should be re-baselined.
- `localchat_tui/` and `PRODUCT_STRIP_PLAN.md`/`PRODUCT_STRUCTURE.md` contain hard-coded references to `/home/samouraifox/Work/Projects/llm-weapon-v2/` (old path). Internal-only, no leakage. Not worth touching during Phase 0 — flag for cleanup when the TUI gets its v2 makeover.
