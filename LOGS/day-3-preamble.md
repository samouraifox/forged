# Day 3 — Preamble: rag/venv recreation

Date: 2026-05-17. Single-step preamble before Phase 3a.

## Why

Carried-over Day 2 finding: `rag/venv/pyvenv.cfg` and the absolute shebangs in `rag/venv/bin/{pip,*}` pointed at `/home/samouraifox/Work/Projects/llm-weapon/...` — the project's pre-rename path. Functional consequence: `rag/venv/bin/pip install ...` silently routed installs through the wrong Python (`#!/.../llm-weapon/.../python3`), so Day 2's `openai` install initially landed in a stale venv. Workaround that day was `rag/venv/bin/python -m pip install ...`. Real fix is recreating the venv from scratch so the absolute paths regenerate against the current project directory.

## What

```bash
rm -rf rag/venv
python3 -m venv rag/venv
rag/venv/bin/python -m pip install --upgrade pip
rag/venv/bin/python -m pip install -r rag/requirements.txt
```

`python3` resolves via mise to `/home/samouraifox/.local/share/mise/installs/python/3.14.3/bin/python3` (no project-level `.mise.toml` or `.tool-versions`; the global default is 3.14.3).

## Verification

`rag/venv/bin/pip` shebang now reads `#!/home/samouraifox/Work/Projects/forged/rag/venv/bin/python` (correct project, no longer `llm-weapon`).

`pyvenv.cfg` `command` field reads `... -m venv /home/samouraifox/Work/Projects/forged/rag/venv` (correct project).

Import smoke from inside the new venv:

```
chromadb 1.5.9
ollama installed
openai 2.37.0
sentence_transformers 5.5.0
bm25s 0.3.9
```

All six requirements from `rag/requirements.txt` import cleanly. The `pip install -r` resolved the full transitive closure including `torch 2.12.0`, `transformers 5.8.1`, `scipy 1.17.1`, `scikit-learn 1.8.0`, and the OpenTelemetry stack pulled by `chromadb`.

## Observation worth recording (not blocking)

`torch 2.12.0` transitively pulled the full `nvidia-cublas-13.x` / `nvidia-cudnn-cu13` / `nvidia-cusparse` / `nvidia-curand` / `nvidia-cufft` / `nvidia-cusolver` / `nvidia-nccl-cu13` / `nvidia-cuda-runtime` stack — ~5 GB of CUDA libraries that will never be exercised on Intel Arc 140V. Day 3 is not the right phase to optimize this (preamble is "restore deps", not "rewrite requirements"); flagging for a future requirements-tightening pass where torch can be installed via `--index-url https://download.pytorch.org/whl/cpu` or replaced with `openvino-runtime`-only paths once the embedder swap lands.

## Files

None changed — `rag/venv/` is gitignored. This log file is the only artifact of the preamble.

Commit is intentionally light. The real Day 3 work begins in Phase 3a.
