from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static, TextArea


class ComposerSubmitted(Message):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class ComposerInput(TextArea):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            "",
            soft_wrap=True,
            tab_behavior="focus",
            compact=True,
            highlight_cursor_line=False,
            placeholder="Message the local model...",
            **kwargs,
        )
        self.cursor_blink = True

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            self.post_message(ComposerSubmitted(self.text))
            event.prevent_default()
            event.stop()
            return
        await super()._on_key(event)


class ChatComposer(Widget):
    class Submitted(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def compose(self) -> ComposeResult:
        with Vertical(id="composer-shell"):
            yield Static("PROMPT", id="composer-label")
            yield ComposerInput(id="composer-input")

    def current_text(self) -> str:
        return self.query_one(ComposerInput).text

    def clear(self) -> None:
        self.query_one(ComposerInput).clear()

    def focus_editor(self) -> None:
        self.query_one(ComposerInput).focus()

    def set_busy(self, busy: bool) -> None:
        editor = self.query_one(ComposerInput)
        editor.read_only = busy
        editor.placeholder = "Local backend is busy..." if busy else "Message the local model..."
        self.query_one("#composer-label", Static).update("BUSY" if busy else "PROMPT")
        self.set_class(busy, "is-busy")

    def on_composer_submitted(self, message: ComposerSubmitted) -> None:
        self.post_message(self.Submitted(message.text))
