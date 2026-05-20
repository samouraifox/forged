"""Headless screenshot capture for the cyberpunk TUI refresh.

Runs the TUI under Textual's test pilot with a stub backend, exporting SVG
screenshots into LOGS/tui-refresh-screenshots/.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from localchat_tui.app import LocalChatApp
from localchat_tui.backend import (
    BackendDescriptor,
    ChatBackendAdapter,
    StreamChannel,
    StreamEvent,
)
from localchat_tui.state import ChatMessage, ConversationState, MessageKind, ModeState


OUT_DIR = ROOT / "LOGS" / "tui-refresh-screenshots"


class StubAdapter(ChatBackendAdapter):
    def __init__(self) -> None:
        self.descriptor = BackendDescriptor(
            provider="llama-server",
            name="hacker_lm",
            model="Hermes-4-14B Q6_K",
            think_control="enabled",
        )

    async def startup(self) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(StreamChannel.STATUS, "loading Hermes-4-14B (Q6_K) via llama.cpp Vulkan...")
        await asyncio.sleep(0.02)
        yield StreamEvent(StreamChannel.STATUS, "KV cache 4-bit · YaRN 64K · ready")

    async def stream_reply(
        self,
        prompt: str,
        conversation: ConversationState,
        modes: ModeState,
    ) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(StreamChannel.STATUS, "")
        yield StreamEvent(StreamChannel.DONE, "")


async def _settle(pilot, ticks: int = 6) -> None:
    for _ in range(ticks):
        await pilot.pause(0.05)


async def capture_landing(app: LocalChatApp, pilot) -> None:
    await _settle(pilot, ticks=10)
    app.save_screenshot(filename="01-landing.svg", path=str(OUT_DIR))
    print(f"saved {OUT_DIR / '01-landing.svg'}")


async def capture_active(app: LocalChatApp, pilot) -> None:
    await app._add_message(
        ChatMessage(
            kind=MessageKind.USER,
            text="Walk me through CVE-2024-3094 — what's the exploitation path and how would I detect a compromised host?",
        )
    )
    await app._add_message(
        ChatMessage(
            kind=MessageKind.THINKING,
            text=(
                "Considering CVE-2024-3094 supply-chain backdoor in xz-utils. "
                "The malicious liblzma replaces an IFUNC resolver and hooks "
                "RSA_public_decrypt in sshd. Detection vector: anomalous RSA "
                "cert in sshd memory; YARA rules on the xz-utils 5.6.0/5.6.1 "
                "blobs."
            ),
        )
    )
    await app._add_message(
        ChatMessage(
            kind=MessageKind.ASSISTANT,
            text=(
                "CVE-2024-3094 is a supply-chain backdoor in xz-utils 5.6.0 and "
                "5.6.1. The malicious liblzma replaces an IFUNC resolver and hooks "
                "RSA_public_decrypt in sshd, letting a remote attacker holding the "
                "matching private key execute arbitrary code pre-authentication.\n\n"
                "Detection: (1) check xz --version on every host — anything ≥5.6.0 "
                "and <5.6.2 is suspect; (2) hash liblzma.so.5 against known-good; "
                "(3) YARA on the IFUNC resolver pattern; (4) audit sshd memory for "
                "the injected RSA public key constant."
            ),
        )
    )
    await _settle(pilot, ticks=15)
    app.save_screenshot(filename="02-active-session.svg", path=str(OUT_DIR))
    print(f"saved {OUT_DIR / '02-active-session.svg'}")


async def capture_mode_pills(app: LocalChatApp, pilot) -> None:
    await pilot.press("f3")
    await _settle(pilot, ticks=3)
    await pilot.press("f4")
    await _settle(pilot, ticks=5)
    app.save_screenshot(filename="03-mode-pills-mixed.svg", path=str(OUT_DIR))
    print(f"saved {OUT_DIR / '03-mode-pills-mixed.svg'}")


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app = LocalChatApp(adapter=StubAdapter())
    async with app.run_test(size=(120, 42)) as pilot:
        await capture_landing(app, pilot)
        await capture_active(app, pilot)
        await capture_mode_pills(app, pilot)


if __name__ == "__main__":
    asyncio.run(main())
