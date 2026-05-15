from __future__ import annotations

from dataclasses import dataclass

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Static

from .backend import ChatBackendAdapter, HackerLMBackendAdapter, StreamChannel
from .state import (
    ChatMessage,
    CommandResult,
    ConversationState,
    MessageKind,
    ModeState,
    apply_slash_command,
)
from .theme import APP_NAME, APP_SUBTITLE, COMPOSER_HINT
from .widgets import AppHeader, ChatComposer, MessageBlock, ModeBar, TranscriptView


@dataclass(slots=True)
class ReplyRenderState:
    thinking_block: MessageBlock | None = None
    answer_block: MessageBlock | None = None


class LocalChatApp(App[None]):
    CSS_PATH = "styles.tcss"
    TITLE = APP_NAME
    SUB_TITLE = APP_SUBTITLE
    BINDINGS = [
        Binding("f2", "toggle_think", "Toggle think", show=False),
        Binding("f3", "toggle_rag", "Toggle rag", show=False),
        Binding("f4", "toggle_ctx", "Toggle ctx", show=False),
        Binding("f5", "focus_topk", "Focus topk", show=False),
        Binding("ctrl+c", "request_quit", "Quit", show=False, priority=True),
        Binding("ctrl+d", "request_quit", "Quit", show=False, priority=True),
    ]

    def __init__(self, adapter: ChatBackendAdapter | None = None) -> None:
        super().__init__()
        self.adapter = adapter or HackerLMBackendAdapter()
        self.modes = ModeState(
            provider=self.adapter.descriptor.provider,
            backend=self.adapter.descriptor.name,
            model=self.adapter.descriptor.model,
            think_control=self.adapter.descriptor.think_control,
        )
        self.conversation = ConversationState()
        self.message_widgets: dict[str, MessageBlock] = {}
        self.session_active = False

    def compose(self) -> ComposeResult:
        with Container(id="layout", classes="session-idle"):
            with Vertical(id="shell", classes="session-idle"):
                yield AppHeader(self.adapter.descriptor, id="app-header")
                yield Static("", id="landing-status")
                yield ModeBar(self.modes, id="mode-bar")
                yield TranscriptView(id="conversation")
                yield Static("", id="composer-divider")
                yield ChatComposer(id="composer")
                yield Static(COMPOSER_HINT, id="footer-hints")

    async def on_mount(self) -> None:
        self.query_one(ModeBar).sync(self.modes)
        self.query_one(ChatComposer).set_busy(True)
        self._set_landing_status("booting local backend runtime...")
        self._refresh_layout_state()
        self.bootstrap_backend()

    async def on_unmount(self) -> None:
        await self.adapter.aclose()

    def action_toggle_think(self) -> None:
        self._flip_mode("think")

    def action_toggle_rag(self) -> None:
        self._flip_mode("rag")

    def action_toggle_ctx(self) -> None:
        self._flip_mode("ctx")

    def action_focus_topk(self) -> None:
        self.query_one(ModeBar).focus_topk()

    def action_request_quit(self) -> None:
        self.exit()

    @on(ChatComposer.Submitted)
    async def handle_composer_submitted(self, message: ChatComposer.Submitted) -> None:
        text = message.text.strip()
        composer = self.query_one(ChatComposer)
        if not text:
            composer.focus_editor()
            return

        composer.clear()
        if text.startswith("/"):
            await self._handle_command(text)
            composer.focus_editor()
            return

        await self._add_message(ChatMessage(kind=MessageKind.USER, text=text))
        composer.set_busy(True)
        self.stream_assistant_reply(text)

    @on(ModeBar.ToggleRequested)
    def handle_mode_toggle(self, message: ModeBar.ToggleRequested) -> None:
        self._flip_mode(message.mode)

    @on(ModeBar.TopKRequested)
    async def handle_topk_requested(self, message: ModeBar.TopKRequested) -> None:
        try:
            value = int(message.raw_value.strip())
            self.modes.set_topk(value)
        except ValueError:
            self.query_one(ModeBar).sync(self.modes)
            await self._add_message(
                ChatMessage(kind=MessageKind.SYSTEM, text="TOPK must be an integer between 1 and 20.")
            )
            return
        self.query_one(ModeBar).sync(self.modes)
        self.query_one(ChatComposer).focus_editor()

    @work(exclusive=True, group="backend", exit_on_error=False)
    async def bootstrap_backend(self) -> None:
        composer = self.query_one(ChatComposer)
        try:
            async for event in self.adapter.startup():
                await self._consume_backend_event(event, ReplyRenderState())
        except Exception as error:
            await self._add_message(ChatMessage(kind=MessageKind.ERROR, text=str(error)))
            composer.set_busy(False)
            composer.focus_editor()
            return
        self._sync_backend_descriptor()
        self._set_landing_status("ready")
        composer.set_busy(False)
        composer.focus_editor()

    @work(exclusive=True, group="chat", exit_on_error=False)
    async def stream_assistant_reply(self, prompt: str) -> None:
        render_state = ReplyRenderState()
        composer = self.query_one(ChatComposer)

        try:
            async for event in self.adapter.stream_reply(prompt, self.conversation, self.modes):
                render_state = await self._consume_backend_event(event, render_state)
        except Exception as error:
            await self._add_message(
                ChatMessage(kind=MessageKind.ERROR, text=f"Backend stream failed: {error}")
            )
        finally:
            self._sync_backend_descriptor()
            composer.set_busy(False)
            composer.focus_editor()

    async def _handle_command(self, raw: str) -> None:
        try:
            result = apply_slash_command(raw, self.modes)
        except ValueError as error:
            await self._add_message(ChatMessage(kind=MessageKind.SYSTEM, text=str(error)))
            self.query_one(ModeBar).sync(self.modes)
            return

        self.query_one(ModeBar).sync(self.modes)
        await self._emit_command_feedback(result)
        if result.exit_requested:
            self.exit()

    async def _emit_command_feedback(self, result: CommandResult) -> None:
        await self._add_message(ChatMessage(kind=MessageKind.SYSTEM, text=result.feedback))

    async def _add_message(self, message: ChatMessage) -> MessageBlock:
        if not self.session_active and message.kind != MessageKind.STATUS:
            self._set_session_active(True)
        self.conversation.add(message)
        transcript = self.query_one(TranscriptView)
        block = await transcript.add_message(message)
        self.message_widgets[message.id] = block
        return block

    async def _consume_backend_event(
        self,
        event,
        render_state: ReplyRenderState,
    ) -> ReplyRenderState:
        transcript = self.query_one(TranscriptView)

        if event.channel == StreamChannel.STATUS and event.text:
            if not self.session_active:
                self._set_landing_status(event.text)
                return render_state
            await self._add_message(ChatMessage(kind=MessageKind.STATUS, text=event.text))
            return render_state
        if event.channel == StreamChannel.RETRIEVED_CONTEXT and event.text:
            await self._add_message(ChatMessage(kind=MessageKind.TOOL, label="CONTEXT", text=event.text))
            return render_state
        if event.channel == StreamChannel.ERROR and event.text:
            await self._add_message(ChatMessage(kind=MessageKind.ERROR, text=event.text))
            return render_state
        if event.channel == StreamChannel.DONE:
            return render_state
        if event.channel == StreamChannel.THINKING:
            if render_state.thinking_block is None:
                thinking_message = self.conversation.add(ChatMessage(kind=MessageKind.THINKING, streaming=True))
                render_state.thinking_block = await transcript.add_message(thinking_message)
                self.message_widgets[thinking_message.id] = render_state.thinking_block
            sticky = transcript.should_stick_to_bottom()
            render_state.thinking_block.append_text(event.text)
            if sticky:
                transcript.follow_tail()
            return render_state
        if event.channel == StreamChannel.ANSWER_CHUNK:
            if render_state.answer_block is None:
                answer_message = self.conversation.add(ChatMessage(kind=MessageKind.ASSISTANT, streaming=True))
                render_state.answer_block = await transcript.add_message(answer_message)
                self.message_widgets[answer_message.id] = render_state.answer_block
            sticky = transcript.should_stick_to_bottom()
            render_state.answer_block.append_text(event.text)
            if sticky:
                transcript.follow_tail()
            return render_state
        return render_state

    def _flip_mode(self, field_name: str) -> None:
        self.modes.toggle(field_name)
        self.query_one(ModeBar).sync(self.modes)

    def _set_landing_status(self, text: str) -> None:
        self.query_one("#landing-status", Static).update(text)

    def _set_session_active(self, active: bool) -> None:
        if self.session_active == active:
            return
        self.session_active = active
        self._refresh_layout_state()

    def _refresh_layout_state(self) -> None:
        layout = self.query_one("#layout", Container)
        shell = self.query_one("#shell", Vertical)
        transcript = self.query_one(TranscriptView)
        landing_status = self.query_one("#landing-status", Static)
        divider = self.query_one("#composer-divider", Static)
        for node in (layout, shell):
            node.set_class(not self.session_active, "session-idle")
            node.set_class(self.session_active, "session-active")
        transcript.display = self.session_active
        divider.display = self.session_active
        landing_status.display = not self.session_active

    def _sync_backend_descriptor(self) -> None:
        self.modes.provider = self.adapter.descriptor.provider
        self.modes.backend = self.adapter.descriptor.name
        self.modes.model = self.adapter.descriptor.model
        self.modes.think_control = self.adapter.descriptor.think_control
        self.query_one(AppHeader).set_descriptor(self.adapter.descriptor)
        self.query_one(ModeBar).sync(self.modes)
