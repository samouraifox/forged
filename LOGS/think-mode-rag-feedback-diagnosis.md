# Think mode + RAG retrieval feedback — diagnosis + fixes

**Date:** 2026-05-20
**Trigger:** Live TUI testing — F2 (think mode) toggled ON but Hermes-4 answered instantly with no thinking gap, no TRACE block; F3 (RAG mode) gave zero visible feedback during retrieval (~7 s of silence before reply streamed).
**Outcome:** Both fixed. F2 ON now triggers Hermes-4 hybrid thinking via system-prompt activation + `chat_template_kwargs`. F3 retrieval now surfaces 6 distinct phase events with prominent `▸ tag · text` styling.

---

## Part A — Think mode

### A1. Request-body diff (THINK ON vs THINK OFF)

`rag/service.py` flow:

```
modes.think (TUI)
  → backend.py payload["modes"]["think"]
    → tui_worker.py → QueryConfig.think
      → service.stream_query → _generate(think=...)
        → _effective_system(system, think)
        → _stream_generate(emit_thinking=think)
```

Pre-fix `_effective_system`:

```python
def _effective_system(self, system: str, think: bool) -> str:
    if think:
        return system                                    # ← no change
    return f"{system}\n\n{NO_THINK_INSTRUCTION}"
```

NO_THINK_INSTRUCTION was the literal string `"Do not use <think> blocks for this response. Answer directly."`

So the only request-body delta between THINK ON and THINK OFF was: when OFF, the NO_THINK suffix is appended to the system message. When ON, the system message is unchanged. **Nothing in either path actively activates thinking** — the logic assumed Hermes-4 emits `<think>` by default and merely needed suppression.

### A2. Hermes-4 activation mechanism

Probed `/props` on the running llama-server (Hermes-4-14B Q6_K, `--jinja` enabled). The chat template's relevant lines:

```jinja
{%- set thinking_prompt = 'You are a deep thinking AI, you may use extremely long chains of thought to deeply consider the problem and deliberate with yourself via systematic reasoning processes to help come to a correct solution prior to answering. You should enclose your thoughts and internal monologue inside <think> </think> tags, and then provide your solution or response to the problem.' %}
{%- set standard_prompt = 'You are Hermes, created by Nous Research.' %}
{%- if not thinking is defined %}{% set thinking = false %}{% endif %}
{%- if thinking %}{%- set system_prompt = thinking_prompt %}{%- else %}{%- set system_prompt = standard_prompt %}{%- endif %}
{%- if messages[0]['role'] == 'system' %}
    {{- '<|im_start|>system\n' + messages[0]['content'] + '<|im_end|>\n' }}
{%- else %}
    {{- '<|im_start|>system\n' + system_prompt + '<|im_end|>\n' }}
{%- endif %}
```

Hermes-4 is OPT-IN to thinking. Activation has two surfaces:

1. **chat_template_kwargs (`{"thinking": true}`):** sets the jinja `thinking` variable so the template picks `thinking_prompt` as the system. But — and this is the critical part — the template **only uses `thinking_prompt` when no user system message is present**. Since `service._stream_generate` ALWAYS provides a custom system (RAG_RUNTIME_SYSTEM or DIRECT_RUNTIME_SYSTEM), the kwargs alone won't activate thinking.
2. **Embedding the thinking directive in the user-supplied system message:** if we include the verbatim Hermes thinking prompt as a prefix to our system, the model engages thinking (it was fine-tuned on this prompt pattern).

#### Curl evidence

**Test 1 (baseline):** No system, no kwargs.

```
curl ... -d '{"messages":[{"role":"user","content":"What is CVE-2022-22965? One sentence."}],"stream":false,...}'
→ {"content":"CVE-2022-22965 is a critical remote code execution ..."}  # 41 tokens, no <think>
```

**Test 2b (chat_template_kwargs only, no user system):** `chat_template_kwargs:{thinking:true}`.

```
curl ... -d '{"messages":[{"role":"user","content":"What is 17 * 13? Show your reasoning."}],"chat_template_kwargs":{"thinking":true},...}'
→ data: {"content":"<think>"}
→ data: {"content":"\n"}
→ data: {"content":"Okay"}
→ data: {"content":","}  ...
```

Thinking engaged.

**Test 3 (custom system + explicit directive):** our pattern.

```
curl ... -d '{"messages":[{"role":"system","content":"You are a deep thinking AI. Enclose your reasoning inside <think>...</think> tags before giving the final answer. The final answer must come AFTER the closing </think> tag.\n\nAnswer in ENGLISH ONLY. Keep the answer direct."},{"role":"user","content":"What is 17 * 13? Show reasoning briefly."}],...}'
→ data: {"content":"<think>"}
→ data: {"content":"\n"}
→ data: {"content":"Okay"}
→ data: {"content":","}  ...
```

Thinking engaged. So embedding the directive in our system message activates thinking even without kwargs.

### A3. Wire activation into F2 toggle (applied)

`rag/service.py`:

- New `THINK_ACTIVATION_PREFIX` constant — verbatim Hermes `thinking_prompt`. When F2 ON, this is **prepended** to whatever system message we already pass (RAG_RUNTIME_SYSTEM or DIRECT_RUNTIME_SYSTEM).
- Removed `NO_THINK_INSTRUCTION` (Hermes defaults to non-thinking — no suppression needed).
- `_effective_system` inverted: `if think: prefix + system`, else `system`.
- `_stream_generate` now also passes `extra_body={"chat_template_kwargs": {"thinking": think}}` so the template's multi-turn CoT-strip logic stays consistent for prior assistant turns.
- `RetrieveService.think_control` descriptor changed `"prompt-policy"` → `"hermes-prefix"` to reflect the activation mechanism.

### A4. Parser + renderer — already correct

`ThinkTagStreamParser` (rag/service.py:262-307) handles character-by-character tag detection and correctly splits chunks into `(in_think, text)` segments — including the partial-tag case where `<think>` arrives across two SSE chunks.

`_stream_generate` (rag/service.py:512-548) emits `QueryEventType.THINKING` events when `in_think=True AND emit_thinking=True`, and `QueryEventType.ANSWER_CHUNK` otherwise.

`tui_worker.py` forwards events as JSON to backend.py:262 which maps `"thinking"` → `StreamChannel.THINKING`.

`localchat_tui/app.py:261-270` handles the THINKING channel by creating a `MessageKind.THINKING` block (label `"TRACE"`, magenta border `#7a1f60`, italic `#7090a0` body) on first event and appending text on subsequent ones.

The full parse → emit → render path was correct. The bug was strictly upstream: no thinking content ever flowed into the parser because Hermes wasn't activated.

### A5. Live verification (service layer)

```
$ rag/venv/bin/python -u -c "<F2 ON test against 'What is 2+2? Answer in one word.'>"
=== F2 ON (RAG OFF) ===
[+0.0s] status: ▸ retrieve · disabled; sending question directly to LLM
[+0.0s] status: ▸ llm · streaming response (think=on)…
[+1.9s] THINK START
[+102.2s] THINK END (859 chars)
[+104.9s] status: ▸ timing · llm=104.93 s
[+104.9s] DONE — answer chars=15
```

F2 ON: 1.9 s to first `<think>` token, 859 chars of thinking content streamed over ~100 s, then the answer ("4") streamed in 15 chars.

```
$ rag/venv/bin/python -u -c "<F2 OFF test, same prompt>"
=== F2 OFF (RAG OFF) ===
[+0.0s] status: ▸ retrieve · disabled; sending question directly to LLM
[+0.0s] status: ▸ llm · streaming response (think=off)…
[+42.7s] status: ▸ timing · llm=42.68 s
[+42.7s] DONE — think=0 answer=382
```

F2 OFF: 0 thinking chars, 382 answer chars in 42.7 s. Direct answer, no `<think>`.

Both states produce the expected behavior. The TUI-side render is unchanged code (already verified correct in A4). User can confirm the visual TRACE-block streaming by launching `./hacker_lm` and asking a reasoning question with F2 ON.

---

## Part B — RAG retrieval feedback

### B1. Pre-fix event emission map

`service.stream_query` previously emitted 2 retrieval-phase events:

```
[retrieve] hybrid search over N chunks…
[retrieve] N candidates in T ms -> reranking
```

…followed by `[timing] search=… rerank=…` (timing summary) and `[llm] streaming response…` (LLM start). The first event fired ~0 s in, the second ~3-7 s in, then immediate LLM streaming. So the user saw 2 status lines during retrieval but the rendering was muted enough that they registered as "silent."

### B2. New status events (applied)

```
▸ retrieve · embedding query…
▸ retrieve · searching corpus (14425 chunks)…
▸ retrieve · reranking N candidates (search took T ms)…
▸ retrieve · context ready (K chunks)
▸ timing · search=…ms  rerank=…ms  retrieval_total=…ms
▸ llm · streaming response (think=…)…
```

Six events instead of two during retrieval, with a clear `▸ tag · text` format that's easier to scan. Live trace from `RetrieveService.stream_query`:

```
[+0.0s] STATUS: ▸ retrieve · embedding query…
[+0.0s] STATUS: ▸ retrieve · searching corpus (14425 chunks)…
[+4.5s] STATUS: ▸ retrieve · reranking 17 candidates (search took 4537 ms)…
[+7.0s] STATUS: ▸ retrieve · context ready (3 chunks)
[+7.0s] STATUS: ▸ timing · search=4537 ms  rerank=2417 ms  retrieval_total=6955 ms
[+7.0s] STATUS: ▸ llm · streaming response (think=off)…
```

The user gets:
- An immediate "embedding query…" beat (so the screen isn't silent at t=0)
- An "searching corpus…" beat that persists during the 4.5 s search wait
- A "reranking N candidates…" beat at the search→rerank boundary
- A "context ready" beat right before LLM streaming starts

### B3. Indicator-style decision

Presented two options (mockups via AskUserQuestion):
- **Option (a):** prominent status lines in transcript — kind-status MessageBlock with bumped CSS (bright cyan, bold, left-aligned, `▸` marker, no italic).
- **Option (b):** inline progress line below ModeBar that updates in place and clears at LLM start.

User selected **Option (a)**.

### B4. CSS bump (applied)

`localchat_tui/styles.tcss` — three CSS-rule blocks updated:

```css
/* alignment: was centered, now left-flush with the chat flow */
MessageBlock.kind-status { align-horizontal: left; }
MessageBlock.kind-system { align-horizontal: center; }   /* (unchanged) */

/* card: was narrow (max-width 92) and centered, now full-width + left indent */
.kind-status .message-card { width: 100%; padding: 0 0 0 2; }
.kind-system .message-card { width: auto; max-width: 92; padding: 0 1; }

/* body: was muted-green italic centered, now bright cyan bold left-aligned */
.kind-status .message-body {
    color: #39c6ff;
    text-align: left;
    text-style: bold;
}
```

CSS validation (textual parser): 73 rules parsed, no errors.

---

## Files modified

| File | Change |
|---|---|
| `rag/service.py` | `THINK_ACTIVATION_PREFIX` added; `NO_THINK_INSTRUCTION` removed; `_effective_system` inverted; `_stream_generate` passes `chat_template_kwargs`; STATUS event text rebranded to `▸ tag · text`; new "embedding query…" + "context ready (K chunks)" events; `think_control` = `"hermes-prefix"`. |
| `localchat_tui/styles.tcss` | `kind-status` MessageBlock split from `kind-system`; alignment left, card full-width, body bright-cyan bold left-aligned. |
| `eval/run_eval.py` | Timing filter updated: `if "[timing]" in event.text or "▸ timing" in event.text:` — keeps eval reproducibility for both old + new STATUS formats. |

## Don't-break checklist (all preserved)

- `_StreamingTagStripper` citation-tag stripping for the DISPLAYED answer — unchanged
- `RetrieveService.retrieve_top_hits` and other eval-facing entry points — unchanged
- Keybindings and mode pill rendering — unchanged
- `rag/config.py` single-source-of-truth defaults — unchanged
- `hacker_lm` launcher's llama-server bring-up — unchanged (still calls `rag.runtime --ensure-ollama`, see Day 8-9 audit note about this being an unused v1 artifact)

## Verification needed manually (next step for orchestrator)

The service-layer behavior is confirmed (curl + python harness). The TUI visual confirmation needs a live `./hacker_lm` run:

1. **Part A**: F2 ON + reasoning question → TRACE block streams for tens of seconds before REPLY block streams.
2. **Part A**: F2 OFF + same question → no TRACE block, near-instant REPLY.
3. **Part B**: F3 ON + CVE question → the inline `#retrieve-indicator` line below the ModeBar updates in place through each phase, then clears when REPLY (or TRACE) starts streaming.

---

## Addendum (2026-05-20, post-pick swap)

User reconsidered the B3 pick — option (a)'s persistent in-transcript status lines visually overlapped with the F4/CTX feature (which already inlines retrieved chunks into the transcript). Swapped to **option (b): single inline progress line below the ModeBar**.

### Changes (commit follows the original commit 208bcb1):

- `localchat_tui/app.py` — added `Static("", id="retrieve-indicator")` between `ModeBar` and `TranscriptView`. Two new helpers `_set_retrieve_indicator(text)` and `_clear_retrieve_indicator()`. `_consume_backend_event` routes STATUS-during-session to the indicator instead of the transcript, and clears it on the first THINKING / ANSWER_CHUNK / ERROR / DONE event.
- `localchat_tui/styles.tcss` — `#retrieve-indicator` styled as a thin (height 1) bright cyan `#39c6ff` bold left-aligned line. `display: none` by default; `display: block` when `.is-active` class is set. Reverted the kind-status MessageBlock CSS to the original muted-green centered italic (kept around for any non-session STATUS events, currently only landing-page paths use that route).
- The `▸ tag · text` status text format is **kept** — it's independent of indicator style. The format reads cleanly in the inline widget.

Service-layer behavior unchanged: 6 STATUS events still fire across retrieval; only their TUI sink changed.

### Verification

CSS still parses cleanly (73 rules, 0 errors). App instantiates. `#retrieve-indicator` rule present, `is-active` toggle rule present. Manual TUI smoke still pending (orchestrator).

