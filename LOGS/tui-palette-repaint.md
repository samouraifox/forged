# TUI palette repaint — cyberpunk → warm-neutral (OpenCode-inspired)

Date: 2026-05-21
Files: `localchat_tui/theme.py`, `localchat_tui/styles.tcss`,
`localchat_tui/widgets/status_bar.py`

## Motivation

The previous cyberpunk palette (neon green `#39ff14` primary, hot magenta
`#ff39c6` + electric cyan `#39c6ff` accents, near-black `#050706`
background) read as "hacker tool from a movie poster." The orchestrator
wanted to move toward "serious infrastructure tool" — closer to
OpenCode CLI, lazygit, k9s, btop in their restrained-palette states.

Visual signature target: warm dark surfaces, off-white primary text,
**one** strong accent (amber) reserved for live/active states, muted
slate for secondary info, the rest in monochrome warm grays.

## Palette decisions

| Role | Old (cyberpunk) | New (warm-neutral) | Notes |
|---|---|---|---|
| Background | `#050706` near-black | `#18181b` Zinc 900 | warm undertone |
| Panel / card bg | `#0a0e0a` | `#1c1917` Stone 900 | slightly warmer than bg |
| Hairline border | `#1a2a1f` | `#27272a` Zinc 800 | |
| Visible border | `#2a3a30` | `#3f3f46` Zinc 700 | |
| Primary text | `#39ff14` neon green | `#fafaf9` Stone 50 | warm cream |
| Muted text | `#5a8060` | `#a8a29e` Stone 400 | |
| Dim / off-state | `#6a8a70` | `#78716c` Stone 500 | |
| Separator dots | `#5a8060` green | `#57534e` Stone 600 | |
| **Live accent** | `#ff39c6` magenta | `#d97706` Amber 600 | borders, indicators |
| Live accent bright | `#ff39c6` | `#fbbf24` Amber 400 | text accent (model name) |
| Info accent | `#39c6ff` cyan | `#94a3b8` Slate 400 | TRACE header, labels |
| Info dim | `#1f607a` | `#64748b` Slate 500 | thinking left-bar |
| Error | `#ff3939` | `#dc2626` Red 600 | softer red |

**Amber discipline**: amber is reserved for elements that signal "live"
or "active state":

- Active mode pill border (THINK/RAG/CTX when on)
- Status-bar mode chips when on
- Status-bar live `●` indicator + model name (the single most important
  live label)
- Composer border when focused
- Retrieve indicator (the `▸ tag · text` line)
- Scrollbar handle when actively scrolling

Everything else is warm grays, off-white, or slate. This gives amber
its semantic weight — if you see it, something is alive on the screen.

## ASCII logo — off-white, not amber

The user spec allowed either off-white `#fafaf9` or soft amber `#fbbf24`
for the logo. Went with **off-white** to keep amber strictly for
live-state semantics. The logo is brand identity, not a live indicator.
The hairline divider below the logo (formerly `#7a1f60` magenta with
`▓▒░` shading) is now plain `─` × 72 in `#3f3f46` warm gray — quiet, no
decoration.

Logo readability check on `#18181b`: off-white `#fafaf9` has ~17:1
contrast — excellent. The filled-block characters (`█` plus the
`╔ ╗ ╚ ╝` ANSI Shadow box-drawing) render cleanly without needing the
previous neon-green brightness.

## TRACE vs REPLY hierarchy

Previously TRACE was magenta-headed and REPLY was bright-green-headed
— both visually loud, fighting for attention. Now:

- **TRACE header**: `#64748b` Slate 500 (left-bar) + `#a8a29e` italic
  body. It's reasoning context — should recede.
- **REPLY header**: `#fafaf9` off-white (left-bar) + `#fafaf9` body.
  Primary content, neutral foreground.

The hierarchy now reads as "secondary context → primary answer"
through brightness alone, no chromatic competition.

## Retrieve indicator

Color changed from `#39c6ff` electric cyan → `#d97706` amber. Behavior
unchanged: thin bold line below the ModeBar, `display: none` by default,
`display: block` when `.is-active`, format `▸ tag · text`. The amber
matches the rest of the live-state vocabulary so the indicator reads
as "something is happening" without needing the previous neon-cyan
shout.

## Status bar — line-by-line color map

**Line 1 (backend identity):**
```
● HERMES-4-14B Q6_K   ·   llama-server   ·   hacker_lm   ·   think:enabled
amber              · = #57534e             stone-400  amber-bright dim sep
amber              ·       slate-400         slate-400  label   value
```

**Line 2 (live state + system):**
```
THINK on  RAG on  CTX off  ·  TOPK 5  ·  SRC ANY  │  RAM 20.8G  ·  UP 00:00:01
amber     amber   dim       sep slate value sep   sep slate value sep slate value
```

Model name is the only `#fbbf24` (amber 400, the brightest amber) — it's
the single most important piece of live information, and the brightness
distinguishes it from the other amber elements.

## Judgment calls

1. **Logo color**: off-white over amber. See "ASCII logo" section above
   — amber discipline.

2. **TRACE in slate vs amber-dim**: slate. Reasoning is *info* not
   *action*. Amber-dim (`#92400e`) would read as "active but quiet,"
   which is wrong semantically.

3. **Removed `╣ provider » model ╠` decorative brackets** in
   `format_backend_line`. Now just `provider · model`. The previous
   box-drawing flourish was cyberpunk-decorative, doesn't fit the new
   tone.

4. **Removed `▓▒░ ═ ═ ═ ░▒▓` patterned divider** under the logo. Now a
   plain `─` × 72 horizontal rule. Quieter; fits the restraint goal.

5. **Composer focus border = amber** (was bright green). This is one of
   the few spots where the user is actively *doing* something, so amber
   fits the "live/active" semantic.

6. **Off-state mode pill text** at `#78716c` (Stone 500) on `#1c1917`
   yields ~4.6:1 contrast. Borderline AA, intentionally muted — readable
   but recedes. If this proves too dim in actual use I'd bump to
   `#a8a29e` Stone 400.

## What stays unchanged

- ASCII logo shape (`██╔══██╗` ANSI Shadow style, 6 rows × 72 cols)
- Mode pill structure (`⟦ ▮ NAME ⟧` / `⟦ · NAME ⟧`), keybindings
  (F2/F3/F4/F5)
- Status bar layout, refresh interval (4 s), fields shown
- Retrieve indicator behavior (6 STATUS events from service.py, `▸ tag ·
  text` format, inline single-line above transcript)
- Streaming pipeline, F2 thinking activation, kind-status message rule
- `LocalChatApp`, `AppHeader`, `ModeBar`, `ChatComposer`, `MessageBlock`,
  `TranscriptView`, `StatusBar` class names
- `hacker_lm` launcher, `requirements-tui.txt`, backend adapter interface

## Screenshots

Saved to `LOGS/tui-refresh-screenshots/`:

- `04-landing-warmneutral.{svg,png}` — logo + mode pills + status bar
- `05-active-trace-reply.{svg,png}` — CVE-2024-3094, F2 on, TRACE → REPLY
- `06-active-retrieve.{svg,png}` — F3 on, retrieve indicator mid-flight

The original cyberpunk screenshots remain archived at filenames
`01-landing.{svg,png}`, `02-active-session.{svg,png}`,
`03-mode-pills-mixed.{svg,png}` for comparison.
