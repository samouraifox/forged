from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "HACKER_LM"
APP_SUBTITLE = "local operator shell · offensive security copilot"
COMPOSER_HINT = (
    "▸ ENTER send  ▸ SHIFT+ENTER newline  "
    "▸ F2 THINK  ▸ F3 RAG  ▸ F4 CTX  ▸ F5 TOPK  "
    "▸ /help  ▸ CTRL+C/D exit"
)


ASCII_LOGO = r"""
 ██╗  ██╗ █████╗  ██████╗██╗  ██╗███████╗██████╗     ██╗     ███╗   ███╗
 ██║  ██║██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗    ██║     ████╗ ████║
 ███████║███████║██║     █████╔╝ █████╗  ██████╔╝    ██║     ██╔████╔██║
 ██╔══██║██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗    ██║     ██║╚██╔╝██║
 ██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║    ███████╗██║ ╚═╝ ██║
 ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝    ╚══════╝╚═╝     ╚═╝
""".strip("\n")


LOGO_DIVIDER = "─" * 72


@dataclass(frozen=True, slots=True)
class Palette:
    """Warm-neutral terminal palette — OpenCode-inspired. Off-white on warm
    dark, with amber reserved for live/active states only."""

    # Surfaces (warm dark, near-black with warm undertone)
    background: str = "#18181b"          # Zinc 900 — primary canvas
    panel: str = "#1c1917"               # Stone 900 — status bar, cards
    panel_alt: str = "#27272a"           # Zinc 800 — focused input bg

    # Borders (hairline → visible)
    border: str = "#27272a"              # Zinc 800 — hairline
    border_dim: str = "#1f1f23"          # subtler than hairline
    border_strong: str = "#3f3f46"       # Zinc 700 — visible card border

    # Text (warm cream rather than cold white)
    text: str = "#fafaf9"                # Stone 50 — primary
    text_bright: str = "#ffffff"         # emphasis only
    muted: str = "#a8a29e"               # Stone 400 — secondary text
    muted_dim: str = "#78716c"           # Stone 500 — tertiary / off-state
    muted_dimmer: str = "#57534e"        # Stone 600 — separators, placeholders

    # Amber — reserved for live/active/primary states
    amber: str = "#d97706"               # Amber 600 — borders, primary accent
    amber_bright: str = "#fbbf24"        # Amber 400 — text accent / model name
    amber_dim: str = "#92400e"           # Amber 800 — subtle live trace

    # Slate — secondary info (TRACE, backend labels)
    slate: str = "#94a3b8"               # Slate 400 — info text
    slate_dim: str = "#64748b"           # Slate 500 — info accent

    # State colors
    error: str = "#dc2626"               # Red 600
    error_bg: str = "#1f1313"            # very dark warm red
    warning: str = "#d97706"             # amber doubles as warning


PALETTE = Palette()


def format_backend_line(provider: str, model: str) -> str:
    return f"{provider} · {model}"
