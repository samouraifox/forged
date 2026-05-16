# forged

Local, uncensored cybersecurity copilot for authorized red-team work. Runs entirely offline on a thin-and-light Intel laptop. v2 — currently rebuilding.

## Status

Active build, not ready for use. Tracking the build day-by-day in [BUILD_JOURNAL.md](./BUILD_JOURNAL.md).

The v1 product (a Textual TUI on top of DeepSeek-R1-abliterated + ChromaDB + BM25 + a cross-encoder reranker) ran. Every layer of it was 1–2 generations behind 2026 state of the art, and the system had no agentic mode, no knowledge graph, and no native tool calling. v2 is an in-place upgrade across the entire stack — measured against an evaluation harness so every change has to move a number or get reverted.

## What it is

A retrieval-augmented generation stack over a curated corpus of public security material (HackTricks, PayloadsAllTheThings, the OWASP Cheat Sheet Series, and MITRE ATT&CK / CTI), with hybrid dense+sparse retrieval, an LLM trained to emit structured tool calls as the reasoning brain, a Pydantic AI agent loop with sandboxed tool execution (nmap, curl, gobuster, sqlmap, nuclei, file, strings, checksec) for hands-on tasks, and a Kuzu knowledge graph layer on top of CVE/CWE/CAPEC/ATT&CK so the system can resolve entity relationships rather than re-deriving them every query.

The user-facing interface is a Textual TUI today, with a custom desktop frontend planned once the v2 stack stabilizes.

## Hardware target

Intel Core Ultra 7 258V (Lunar Lake), Intel Arc 140V iGPU, 30 GB shared LPDDR5x RAM, no NVIDIA. The model, the embedding model, the reranker, the vector DB, and the knowledge graph all share the same memory pool the OS is using. The build is constrained by what an iGPU can run — most of the design decisions downstream of this fall out of that constraint.

## Stack (v2 target)

| Layer | Choice |
|---|---|
| Model | `NousResearch/Hermes-4-14B` Q6_K (Qwen3-14B base, RL post-trained, native `<tool_call>` tokens, Apache-2.0) |
| Runtime | `llama-server` (llama.cpp Vulkan), `--jinja`, YaRN to 64K context, Q8 KV cache |
| Embeddings | Qwen3-Embedding-0.6B via OpenVINO GenAI |
| Sparse retrieval | BM25s |
| Reranker | Qwen3-Reranker-0.6B (OpenVINO) |
| Vector DB | Chroma |
| Graph DB | Kuzu (embedded, loaded from MITRE/NIST canonical feeds) |
| Chunking | Markdown-aware + Anthropic Contextual Retrieval prepending at index time |
| Orchestration | LangGraph adaptive state machine (CRAG-style relevance grading + HyDE + multi-query) |
| Agent loop | Pydantic AI |
| Sandbox | bubblewrap + seccomp + Landlock, absolute-path binary allowlist |
| Frontend | Textual TUI now, custom desktop later (Tauri+SolidJS or Open WebUI fork — TBD) |

The v1 stack still in this tree (DeepSeek-R1-abliterated, `nomic-embed-text`, the MiniLM reranker, the existing TUI) is the baseline the v2 upgrades are measured against — not the final product.

As of Day 2, generation runs via `scripts/llama-server.sh` (llama.cpp Vulkan, Hermes-4-14B Q6_K); Ollama is retained only for embeddings.

## Why not just use ChatGPT / Claude / a hosted RAG

Authorized red-team and pentest work involves discussing offensive techniques, payloads, CVE exploitation primitives, and target reconnaissance against systems you own or are contracted to test. Hosted assistants either refuse on alignment grounds, leak query content to provider infrastructure, or both. A local stack avoids both problems: no data leaves the laptop, no third-party content policy gates the answer, and the same machine can run the assistant on an airgapped engagement. The tradeoff is that you give up frontier-model quality and accept whatever a 14B local model can do — which is why most of the v2 build is about extracting the maximum useful work from that constraint.

## Setup

See [CORPUS_SETUP.md](./CORPUS_SETUP.md) for corpus population and [BUILD_JOURNAL.md](./BUILD_JOURNAL.md) for the build narrative. Full quickstart will land when v2 stabilizes.

## License

Apache 2.0. See [LICENSE](./LICENSE).

## Acknowledgements

- **NousResearch** — Hermes-4-14B
- **Qwen team** — Qwen3 base model, embeddings, reranker
- **Anthropic** — Contextual Retrieval pattern
- **HackTricks**, **swisskyrepo/PayloadsAllTheThings**, **OWASP Cheat Sheet Series**, **MITRE ATT&CK / CTI** — corpus material (sourced upstream, not redistributed in this repo)
