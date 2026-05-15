from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from ..state import ChatMessage


class MessageBlock(Widget):
    def __init__(self, message: ChatMessage, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message
        self.add_class(f"kind-{message.kind.value}")
        if message.streaming:
            self.add_class("is-streaming")

    def compose(self) -> ComposeResult:
        with Vertical(classes="message-card"):
            if self.message.label:
                yield Static(self.message.label, classes="message-label")
            yield Static(self.message.text, classes="message-body")

    def append_text(self, chunk: str) -> None:
        if not chunk:
            return
        self.message.append(chunk)
        self.query_one(".message-body", Static).update(self.message.text)
        self.refresh(layout=True)

    def set_text(self, text: str) -> None:
        self.message.text = text
        self.query_one(".message-body", Static).update(self.message.text)
        self.refresh(layout=True)


class TranscriptView(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Vertical(id="transcript-column")

    async def add_message(self, message: ChatMessage) -> MessageBlock:
        stick_to_bottom = self.should_stick_to_bottom()
        block = MessageBlock(message)
        await self.query_one("#transcript-column", Vertical).mount(block)
        if stick_to_bottom:
            self.call_after_refresh(self.scroll_end, animate=False)
        return block

    def should_stick_to_bottom(self) -> bool:
        return (self.max_scroll_y - self.scroll_y) <= 3

    def follow_tail(self) -> None:
        self.call_after_refresh(self.scroll_end, animate=False)
