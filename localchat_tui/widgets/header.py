from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from ..backend import BackendDescriptor
from ..theme import APP_NAME, APP_SUBTITLE, format_backend_line


class AppHeader(Widget):
    def __init__(self, descriptor: BackendDescriptor, **kwargs) -> None:
        super().__init__(**kwargs)
        self.descriptor = descriptor

    def compose(self) -> ComposeResult:
        yield Static(APP_NAME, id="app-title")
        yield Static(APP_SUBTITLE, id="app-subtitle")
        yield Static(self._backend_line(), id="backend-line")

    def set_descriptor(self, descriptor: BackendDescriptor) -> None:
        self.descriptor = descriptor
        if self.is_mounted:
            self.query_one("#backend-line", Static).update(self._backend_line())

    def _backend_line(self) -> str:
        return format_backend_line(
            self.descriptor.provider,
            self.descriptor.model,
        )
