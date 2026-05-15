from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "HACKER_LM"
APP_SUBTITLE = "local operator shell for offensive security workflows"
COMPOSER_HINT = "Enter send  Shift+Enter newline  F2 THINK  F3 RAG  F4 CTX  F5 TOPK  /help  Ctrl+C/D exit"


@dataclass(frozen=True, slots=True)
class Palette:
    background: str = "#05070b"
    panel: str = "#0c1118"
    panel_alt: str = "#0f151d"
    border: str = "#1e2734"
    accent: str = "#8fb7a8"
    accent_soft: str = "#6d8f9d"
    text: str = "#e9eef6"
    muted: str = "#738092"
    thinking: str = "#8d97a6"
    user: str = "#99bff0"
    tool: str = "#d8c095"


PALETTE = Palette()


def format_backend_line(provider: str, model: str) -> str:
    return f"{provider} / {model}"
