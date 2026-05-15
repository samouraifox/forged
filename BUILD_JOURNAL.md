# Build Journal — `forged`

A local, uncensored cybersecurity copilot. v2 of an earlier project (`llm-weapon`), built for authorized red-team and pentest work on a thin-and-light Intel laptop with no NVIDIA GPU. Brand name still TBD — leaning *Metis* (Greek for cunning intelligence) or *Dolos* (Greek for the craft of deception); the working directory is `forged` because that's what it is.

This journal documents the build start to finish. Chapters are written as work happens. Chapter 0 is the planning backfill — everything that happened before the first line of code.

---

## Chapter 0 — The Setup

> *"i found out about a 14B model that might be usefull NousCoder-14B."* — and three sub-agents later, we were still recommending the same model we started with. The setup phase of this project was, on paper, "pick a model and start building." In practice, it was three weeks of cross-checking, rejecting tempting answers, and exposing a series of small traps that would have quietly degraded the final product if we'd taken any of them. This chapter is about those traps.

### Where we started

Project v1 was already a working local cybersecurity assistant — a Textual TUI on top of an Ollama-served local model, with a hybrid RAG stack (ChromaDB + BM25s + a cross-encoder reranker) over HackTricks, PayloadsAllTheThings, the OWASP Cheat Sheet Series, and MITRE ATT&CK. The model was `huihui_ai/deepseek-r1-abliterated:14b`. The embeddings were `nomic-embed-text`. The reranker was `cross-encoder/ms-marco-MiniLM-L-6-v2`. The TUI exposed THINK/RAG/CTX toggles and a TOPK control.

It worked. But by May 2026, every component above was 1–2 generations behind state of the art, the agent could only *describe* offensive operations rather than perform them, there was no knowledge graph layer to handle CVE/ATT&CK relationships, the reasoning was constrained by a model whose `<think>` toggle behavior had degraded under abliteration, and the TUI ceilinged out at chat — no tool-call cards, no citation panel, no findings graph, none of the surfaces a 2026 AI product is expected to have.

The choice was either to ship a thin "model swap" patch or do a real v2. We chose v2.

### The hardware reality

Before any model decisions, the hardware dictates what's possible. This project runs on an Intel Core Ultra 7 258V (Lunar Lake architecture), with an Intel Arc 140V integrated GPU and 30 GB of shared LPDDR5x RAM. There is no NVIDIA GPU. There is no discrete VRAM — everything the model touches is the same memory pool the operating system is using.

This constraint shapes everything downstream:

- The model has to fit in ~10–15 GB while leaving the OS, the RAG index, an embedding model, a reranker, and a graph database in the same pool.
- CUDA-specific kernels (vLLM FlashAttention paths, certain MoE fused kernels) are out.
- The inference runtime must support Vulkan or SYCL backends.

We discovered, in passing, that two of the obvious inference paths were already dead: Intel's `IPEX-LLM` repository was archived in January 2026 (Intel upstreamed fixes into PyTorch 2.9 and stopped maintaining their fork), and the SYCL build of llama.cpp had k-quant correctness issues on the Xe2 architecture that the 140V uses. The only well-validated path left was **llama.cpp's Vulkan backend** — which, fortunately, is fast (~17–18 tok/s on a 14B Q4 model, ~600 tok/s prefill).

That decision quietly locked many downstream choices: GGUF model formats (not Safetensors-only), no SageMaker-served inference, and a preference for models in the Qwen3 lineage because they're the most validated under llama.cpp Vulkan on Arc 140V.

### The model hunt — and why every interesting answer was wrong

The obvious upgrade was `huihui_ai/qwen3-abliterated:14b`. Same publisher as the existing model, newer base (Qwen3 instead of DeepSeek-R1-Distill-Qwen), same abliteration recipe. It would have been the five-minute decision. We didn't take it.

Two separate research passes — once on "best small reasoning models in May 2026" generally, then again specifically focused on "lesser-known but better options ≤20B" — surfaced a long list of tempting alternatives, each with a hidden disqualifier:

- **WhiteRabbitNeo / DeepHat-V1-7B** — looks like the answer for cybersec (security-domain finetune, uncensored). Reality: Qwen2.5-Coder base (older/weaker), V1 doesn't actually claim to be uncensored, and the actually-uncensored V2 is closed-weights from a commercial vendor.
- **Foundation-Sec-8B-Reasoning** (Cisco, January 2026) — strongest cybersec knowledge of anything we tested (CTI-MCQA 69.1, beats GPT-5-nano on CVE→CWE mapping). Reality: HarmBench 93%, LlamaGuard 98.25% — Cisco explicitly *trained it to refuse* offensive content generation. Useful as a silent classifier sidecar, useless as a primary brain.
- **Dolphin 3.0-R1-Mistral-24B** — natively uncensored, strong reasoning distillation. Reality: 24B is over the parameter cap, the R1-distilled reasoning chains balloon agent-loop latency 2–3×, and Mistral is less validated than Qwen3 on Arc 140V.
- **NousResearch/NousCoder-14B** (January 2026) — same publisher as the model we ended up choosing, Qwen3-14B base, fresh RL training. Reality: the reward signal was binary pass/fail on Codeforces-style competitive programming judge tests. Nous published *zero* non-code benchmarks — no MMLU-Pro, no GPQA, no AIME, no BFCL. The omission is the signal: narrow-reward RL is well-documented to regress non-target capabilities, and the maintainer's silence on whether reasoning, tool-calling, or alignment behavior survived is itself the disqualifier. The +7 points on LiveCodeBench v6 don't pay back the lost properties.
- **Phi-4-Reasoning, Command-R7B, GPT-OSS-20B-abliterated, the xLAM/Hammer/watt-tool function-calling specialists** — each rejected for a different concrete reason (broken Pydantic-AI tool format, non-commercial license + AUP forbidding offensive use, unverified MoE path on Arc 140V, weak general reasoning, respectively).

The model we landed on was **`NousResearch/Hermes-4-14B`**. Same Qwen3-14B base as the abliterated baseline we considered, but post-trained differently — by reinforcement learning rather than weight surgery. Three specific properties made it irreplaceable:

1. **Pydantic-schema-valid output was literally the RL reward signal during training.** This is unusual and decisive. The agent loop we planned for v2 uses Pydantic AI to validate every tool call against a typed schema; choosing a model that was rewarded during training for producing those exact structures is the cleanest integration possible.
2. **Native `<tool_call>` tokens are baked into the vocabulary** with first-class parser support in vLLM and SGLang. We're not prompt-engineering tool-call format compliance — the model knows.
3. **RefusalBench 59.5 (low) achieved by RL on a neutrality corpus, not by abliteration.** Abliteration "fixes" refusal by surgically rotating refusal directions out of the residual stream, which causes measurable collateral damage to structured output and chain-of-thought stability. RL training that broadens the response distribution while down-weighting refusal preserves coherence. The benchmarks bear this out: Hermes-4-14B scores MMLU-Pro 80.7 / GPQA-Diamond 60.2 — *above* the stock Qwen3-14B-Thinking it was post-trained from. Abliteration would have landed slightly below.

That last point matters disproportionately, because it intersects with a larger pattern we kept hitting: specialized models lose general capability. Cisco's Foundation-Sec lost compliance. WhiteRabbitNeo lost reasoning depth. NousCoder lost everything except Codeforces performance. The *general* model with *low-damage* post-training was the right primary brain. Specialization gets added later as pluggable LoRA adapters — never as the foundation.

### The fine-tune-first instinct, and why we said no

> *"I honestly want to start working on the finetune first of the LLM, then add the rag and everything on top of it. Since the LLM is the 'brains' it is also the base."*

This was the most consequential moment in the planning phase. It's also the moment where, looking back, the project nearly took a much worse path.

The reasoning sounded reasonable: fine-tune the model on cybersecurity-specific reasoning, then mount RAG and agentic features on a stronger foundation. It is the architectural intuition from traditional software — build the core first, add features on top.

It is wrong for LLMs. Five concrete reasons (now permanently locked into the project memory so future sessions can't relitigate it):

1. **Without an evaluation harness, fine-tuning lift is unmeasurable.** This is *exactly* the failure mode of WhiteRabbitNeo, Foundation-Sec-Reasoning, and the entire family of "we fine-tuned for cyber!" models — they shipped without eval-validated lift, and the regressions were discovered in production. Repeating that pattern on our own model would silently produce a worse v2.
2. **The fine-tune dataset is downstream of RAG quality.** Synthetic training data, in any realistic pipeline, gets generated from the corpus chunks. The corpus chunks get their semantic density from contextual retrieval (Anthropic's pattern — LLM-prepended context per chunk before embedding). If you fine-tune before upgrading the retrieval stack, you train on *worse* data than you'd have had if you'd waited one phase.
3. **Hermes-4-14B may already be strong enough.** The marginal lift from a generic cyber fine-tune over a model that's already operator-styled, uncensored, and reasoning-capable is unproven. We can only know by measuring.
4. **Iteration speed asymmetry.** A RAG change iterates in seconds. A fine-tune iterates in hours and a small AWS bill. Doing the slowest, most expensive loop first — while learning what works — is bad sequencing.
5. **Risk concentration.** A v2 whose entire value depends on a fine-tune that may or may not move the number is a single-point-of-failure project. A v2 whose value comes from a stack of measured RAG improvements, with fine-tuning as a *targeted* later addition, de-risks every phase.

The corrected sequence: build the eval harness first (Day 1, non-negotiable), swap in Hermes-4-14B and measure (Day 2), upgrade embeddings and reranker and measure (Days 3–4), add contextual retrieval and measure (Days 5–6), generate synthetic reasoning exemplars and measure (Day 7), build the agentic loop and measure (Week 2). Fine-tuning becomes Phase v2.5 — gated on the eval revealing specific domain gaps that the RAG upgrades didn't close.

The single non-negotiable rule across all of this: every change must move the eval number, or it gets reverted. Borrowed from a prior incident (memorialized internally as "the NovaCore 2.0 lesson") where a single-shot build delivered 35/200 working devices because the kickoff prompt allowed "12/13 PASS" tolerance and didn't ban "representative coverage" rationalizations. Engineering discipline without measurement isn't engineering.

### The data pipeline — borrowed ground truth, transformed voice

Once the model and sequencing were locked, attention turned to the training and exemplar data. The naive plan was pure synthetic generation: prompt a frontier model to produce `(question, multi-step reasoning, answer)` triples grounded in our corpus chunks, use them to enrich RAG and (later) to fine-tune.

That plan was missing the existing-data leg. By May 2026 there is a real catalog of public cybersecurity datasets — CVEfixes (27k vuln→fix pairs, CC0), the CISA Known Exploited Vulnerabilities catalog (public domain), HackerOne's public bug-bounty disclosures, SpecterOps and TrustedSec public reports, MITRE ATT&CK's structured JSON exports, the National Vulnerability Database. These are *real-world ground truth* that pure generation can't match.

But they aren't usable raw. Most of them are in the wrong voice (academic, defensive, sanitized, or QA-without-CoT), and many have license gotchas (Llama-derivative restrictions, Cohere AUPs forbidding offensive use, per-program disclosure rules).

The pipeline that emerged is hybrid:

1. **Existing datasets** seed each adapter's domain (CVEfixes for CVE analysis, SpecterOps writeups for AD attack chains, HackerOne reports for web bug-bounty patterns, flAWS/CloudGoat writeups for cloud attack surfaces, public engagement reports for report writing).
2. **A frontier model — specifically DeepSeek-R1 via Amazon Bedrock — transforms each seed entry** into the target format and voice. R1 was chosen carefully: it emits native reasoning traces (so the chain-of-thought *is* the output, no prompt engineering needed), it is less aligned on offensive content than Anthropic or OpenAI models (cleaner cooperation on authorized red-team content), and it costs $0.55–$1.35 per million input tokens depending on the route — roughly $50 for the entire transformation pass.
3. **We explicitly chose not to use Claude for this step.** Even when Claude cooperates with the content, it adds a hedged voice ("in an authorized context…") that would pollute the operator-style output via retrieved exemplars. Distribution mismatch between training/RAG and inference is the real cost, not refusal.
4. **Eval-set decontamination** is mandatory — any training example whose question appears in the eval set gets deduplicated. CVE-overlap is the highest risk.
5. **Hand-curation of the top 5–10%** establishes a voice/quality reference before bulk training.

### The compute path — credits, quotas, and the SageMaker pivot

The fine-tuning phase (v2.5, sequenced after v2 ships) needs cloud compute. We had $100 in AWS credits, expiring November 2026.

The first attempt was the obvious EC2 path: spin up a g6.2xlarge spot instance, install Axolotl or Unsloth, run QLoRA. The first CloudShell check revealed the obvious-path doesn't work — the EC2 "All G and VT Spot Instance Requests" vCPU quota was 0 by default. Filing a quota increase is free, takes 24–72 hours, and *probably* would have worked. But there's a cleaner route on a new AWS account: **SageMaker training jobs use a separate quota system**, and their managed-spot training is, at $0.37/hour for ml.g6.2xlarge, roughly half the cost of equivalent raw EC2 spot.

The new path: SageMaker managed-spot training. Same hardware (24 GB L4 GPU, sufficient for QLoRA on a 14B model), same software, lower price, simpler operational story. Two quota requests went in — spot training (`L-BC684567`, request id `6a68d1bb…`) and on-demand fallback (`L-A1025C0C`, request id `c23c522d…`), each asking for 8 vCPUs. Both pending as of journal time. The Bedrock side — needed for data generation, on a completely independent quota path — was verified working in the Playground the same day.

The economics: ~$50 of credits for the data-generation pass (Bedrock DeepSeek-R1 transforming ~5,000 seed entries into our voice), ~$30–40 for the five LoRA training runs (one per adapter: Windows AD, CVE analyst, web app, cloud, report-style), ~$10 iteration buffer. Total ~$90–100 — fits the credit envelope with room for one wrong turn.

### The naming exploration

Branding came up late in planning because we needed to keep working before committing publicly. Two principles emerged:

First, Nous Research's naming pattern is the right register — a single ancient Greek word whose original meaning maps precisely onto what the thing does. Their model `Hermes` (god of boundary crossing) is an instruction model that crosses task boundaries. Their RL environment `Atropos` (the Fate who cuts the thread) terminates training trajectories. The naming *is* the architecture diagram in one word. We wanted to operate in that register, not in the "AI"/"GPT"/"Co" suffix register that defines most 2026 launches.

Second, the word has to be both philosophically right and *commercially available*. The first pick — **METIS** (Greek for cunning intelligence, the specific cognitive mode of Odysseus and of a senior pentester) — passed the first test and partially failed the second. The prestige domains (`metis.ai`, `metis.io`, `metis.sh`) are all taken, including by an active Ethereum L2 blockchain. More problematically, there is an active cybersecurity services company called **Metis Cyber LLC** in Salt Lake City, with `metiscyber.com`, offering "IT, Security, and Dev services" — the exact vertical. Brand collision in the same industry is meaningful for SEO and material for trademark concerns if we commercialize.

The runner-up that emerged was **DOLOS** — Greek personification of trickery, deception, and craft. Where Metis is the *cognitive faculty* of cunning, Dolos is the *act* of deception itself. Arguably tighter to authorized red-team work. `dolos.sh` and `dolos.security` are both available. No active cybersecurity company holds the name.

The decision was deferred. The working directory was named `forged` — a craft-coded word with no commitment, easy to type, autocomplete-friendly, and capable of either becoming the brand or remaining the codebase identity once a public brand is chosen. (Vercel-the-company runs a repo called `next.js`, not `vercel`; codebase identity and brand identity are allowed to differ.)

### The workflow — orchestrator and builder

The final piece of setup was the *how*. Rather than having one Claude Code session handle both planning and building — which produces a context window full of planning conversation that crowds out implementation detail — we split the work:

- **Orchestrator** session, opened from the parent `~/Work/Projects/` directory, holds the project plan, drives task selection, writes briefs, and reviews builder reports. This journal is written by the orchestrator.
- **Builder** session, opened from inside `~/Work/Projects/forged/`, executes briefs, writes per-task technical logs to `LOGS/`, appends to `DECISIONS.md`, and emits a structured report at the end of each task.

A symlink between the two sessions' memory directories means both see the same project memory (`project_forged.md`) as a shared source of truth. Decisions, plans, and locked architectural commitments are persisted to memory; ephemeral conversation context is allowed to disappear. The user pastes prompts and reports between the two sessions as the integration layer.

This separation has a side benefit for this journal: the orchestrator writes the narrative, the builder writes the technical record, and the two artifacts can be combined later into the long-form writeup.

### What we're walking into

When this chapter closes, the state of the world is:

- **Stack decisions locked** in memory: Hermes-4-14B Q6_K + YaRN-64K + llama.cpp Vulkan + Qwen3-Embedding-0.6B + Qwen3-Reranker-0.6B + Anthropic-style contextual retrieval + LangGraph adaptive RAG + Kuzu knowledge graph (CVE/CWE/CAPEC/ATT&CK loaded from canonical MITRE/NIST feeds) + Pydantic AI agent loop + bubblewrap sandbox.
- **Build sequence locked**: Day 1 eval harness (non-negotiable), Days 2–6 retrieval-stack upgrades with eval gating after each, Day 7 synthetic exemplar generation via DeepSeek-R1, Week 2 LangGraph + KG + agent + sandbox.
- **AWS state**: Bedrock confirmed, two quota requests pending for SageMaker training.
- **Memory state**: full plan plus rejected alternatives plus v3+ parked ideas persisted across sessions.
- **Tooling state**: orchestrator and builder workflow defined, symlinked memory, kickoff prompt written.

The first line of code has not been written. The next chapter — Phase 0, Day 1 — is the eval harness, which is the tripwire for every change that follows.

---

*Chapter 1 (Day 1 — Eval Harness) will be written after the builder ships the first task.*

## Sources and references

- Hermes 4 technical report: arXiv 2508.18255
- Qwen3 technical report: arXiv 2505.09388
- Anthropic Contextual Retrieval: Anthropic Cookbook (contextual embeddings guide)
- NousCoder-14B announcement: nousresearch.com/nouscoder-14b-a-competitive-olympiad-programming-model
- Foundation-Sec-8B-Reasoning: Cisco blog, January 2026
- DeepHat-V1-7B (formerly WhiteRabbitNeo): huggingface.co/DeepHat/DeepHat-V1-7B
- IPEX-LLM archival notice: github.com/intel/ipex-llm
- llama.cpp Vulkan performance scoreboard: knightli.com (April 2026 GPU benchmark)
- Magpie data synthesis: arXiv 2406.08464
- Berkeley Function Calling Leaderboard: gorilla.cs.berkeley.edu/leaderboard.html
