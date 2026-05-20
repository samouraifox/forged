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


LOGO_DIVIDER = "▓▒░ " + "═" * 64 + " ░▒▓"


@dataclass(frozen=True, slots=True)
class Palette:
    """Cyberpunk terminal palette — green-on-black with magenta/cyan accents."""

    background: str = "#050706"
    panel: str = "#0a0e0a"
    panel_alt: str = "#0d1410"
    border: str = "#1a2a1f"
    border_dim: str = "#0f1a14"

    text: str = "#c8f5d4"
    text_bright: str = "#39ff14"
    muted: str = "#5a8060"
    muted_dim: str = "#3a5a40"

    accent_magenta: str = "#ff39c6"
    accent_magenta_dim: str = "#7a1f60"
    accent_cyan: str = "#39c6ff"
    accent_cyan_dim: str = "#1f607a"

    thinking: str = "#7090a0"
    user: str = "#39c6ff"
    tool: str = "#ffaa00"
    error: str = "#ff3939"
    warning: str = "#ffaa00"


PALETTE = Palette()


def format_backend_line(provider: str, model: str) -> str:
    return f"╣ {provider} » {model} ╠"
