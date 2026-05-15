# Corpus Setup

The retrieval index in `rag/chroma_db/` is built from four upstream public corpora. They are not redistributed in this repo; you source them directly from their canonical repositories before running ingestion.

## Required layout

`rag/ingest.py` expects exactly these directory names under `rag/corpus/`:

```
rag/corpus/
├── hacktricks/
├── PayloadsAllTheThings/
├── CheatSheetSeries/
└── cti/
```

Renaming or relocating any of these will break ingestion.

## Populate from upstream

From the repo root:

```bash
mkdir -p rag/corpus
cd rag/corpus
git clone --depth=1 https://github.com/HackTricks-wiki/hacktricks.git
git clone --depth=1 https://github.com/swisskyrepo/PayloadsAllTheThings.git
git clone --depth=1 https://github.com/OWASP/CheatSheetSeries.git
git clone --depth=1 https://github.com/mitre/cti.git
```

`--depth=1` keeps each clone small. We do not use git submodules — the corpora are not versioned with our code; we pull whatever upstream currently looks like, ingest it, and rely on the chunk IDs in the index as the stable reference.

## Build the index

After cloning, build the Chroma + BM25 index. The script must run from `rag/` because the corpus paths in `ingest.py` are relative to that directory.

```bash
cd rag
venv/bin/python ingest.py --reset
```

Expect a multi-minute embedding pass against the local `nomic-embed-text` model on the v1 stack. v2 will swap this for Qwen3-Embedding-0.6B; the ingest interface is expected to stay the same.

## Notes

- These corpora are licensed under their respective upstream licenses (HackTricks under CC BY-NC-SA, PayloadsAllTheThings under MIT, OWASP Cheat Sheet Series under CC BY-SA 4.0, MITRE CTI under Apache-2.0 / TLP:CLEAR). They are not redistributed in this repo; the licenses are respected by sourcing them directly upstream.
- `rag/corpus/` is gitignored. The empty placeholder directory exists so the ingest script's path lookups don't fail before you populate it.
