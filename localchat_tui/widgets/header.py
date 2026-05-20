from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from ..backend import BackendDescriptor
from ..theme import APP_NAME, APP_SUBTITLE, ASCII_LOGO, LOGO_DIVIDER, format_backend_line


class AppHeader(Widget):
    def __init__(self, descriptor: BackendDescriptor, **kwargs) -> None:
        super().__init__(**kwargs)
        self.descriptor = descriptor

    def compose(self) -> ComposeResult:
        yield Static(ASCII_LOGO, id="ascii-logo")
        yield Static(LOGO_DIVIDER, id="logo-divider")
        yield Static(APP_NAME, id="app-title")
        yield Static(APP_SUBTITLE, id="app-subtitle")
        yield Static(self._backend_line(), id="backend-line")

    def set_descriptor(self, descriptor: BackendDescriptor) -> None:
        self.descriptor = descriptor
        if self.is_mounted:
            self.query_one("#backend-line", Static).update(self._backend_line())

    def set_session_active(self, active: bool) -> None:
        if not self.is_mounted:
            return
        self.query_one("#ascii-logo", Static).display = not active
        self.query_one("#logo-divider", Static).display = not active

    def _backend_line(self) -> str:
        return format_backend_line(
            self.descriptor.provider,
            self.descriptor.model,
        )
