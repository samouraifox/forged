from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Static

from ..state import ModeState


def _pill_label(name: str, active: bool) -> str:
    indicator = "▮" if active else "·"
    return f"⟦ {indicator} {name} ⟧"


class ModeBar(Widget):
    class ToggleRequested(Message):
        def __init__(self, mode: str) -> None:
            super().__init__()
            self.mode = mode

    class TopKRequested(Message):
        def __init__(self, raw_value: str) -> None:
            super().__init__()
            self.raw_value = raw_value

    def __init__(self, modes: ModeState, **kwargs) -> None:
        super().__init__(**kwargs)
        self.modes = modes

    def compose(self) -> ComposeResult:
        with Container(id="mode-row"):
            with Horizontal(id="mode-cluster"):
                yield Button(_pill_label("THINK", self.modes.think), id="think-toggle", classes="mode-pill")
                yield Button(_pill_label("RAG", self.modes.rag), id="rag-toggle", classes="mode-pill")
                yield Button(_pill_label("CTX", self.modes.ctx), id="ctx-toggle", classes="mode-pill")
                with Horizontal(id="topk-shell", classes="mode-pill"):
                    yield Static("TOPK", id="topk-label")
                    yield Input(value=str(self.modes.topk), id="topk-input", classes="topk-input")

    def on_mount(self) -> None:
        self.sync(self.modes)

    def sync(self, modes: ModeState) -> None:
        self.modes = modes
        if not self.is_mounted:
            return
        for mode_name in ("think", "rag", "ctx"):
            button = self.query_one(f"#{mode_name}-toggle", Button)
            active = getattr(modes, mode_name)
            button.label = _pill_label(mode_name.upper(), active)
            button.remove_class("is-on")
            button.remove_class("is-off")
            button.add_class("is-on" if active else "is-off")
        self.query_one("#topk-input", Input).value = str(modes.topk)

    def focus_topk(self) -> None:
        self.query_one("#topk-input", Input).focus()

    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.endswith("-toggle"):
            self.post_message(self.ToggleRequested(button_id.removesuffix("-toggle")))

    @on(Input.Submitted, "#topk-input")
    def handle_topk_submitted(self, event: Input.Submitted) -> None:
        self.post_message(self.TopKRequested(event.value))
