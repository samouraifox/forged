from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class MessageKind(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    THINKING = "thinking"
    SYSTEM = "system"
    STATUS = "status"
    TOOL = "tool"
    ERROR = "error"


DEFAULT_LABELS: dict[MessageKind, str] = {
    MessageKind.USER: "PROMPT",
    MessageKind.ASSISTANT: "REPLY",
    MessageKind.THINKING: "TRACE",
    MessageKind.SYSTEM: "",
    MessageKind.STATUS: "",
    MessageKind.TOOL: "CONTEXT",
    MessageKind.ERROR: "ERROR",
}

VALID_SOURCE_FILTERS = ("hacktricks", "mitre", "owasp", "payloads")

HELP_TEXT = """\
Commands:
/think on|off   Toggle reasoning stream
/rag on|off     Toggle retrieval mode
/ctx on|off     Show retrieved chunks when RAG is on
/topk <n>       Set retrieval depth between 1 and 20
/source NAME    Filter retrieval to one source or 'none'
/state          Show current mode values
/help           Show command help
/quit           Exit the app"""


@dataclass(slots=True)
class ChatMessage:
    kind: MessageKind
    text: str = ""
    label: str | None = None
    streaming: bool = False
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        if self.label is None:
            self.label = DEFAULT_LABELS[self.kind]

    def append(self, chunk: str) -> None:
        self.text += chunk


@dataclass(slots=True)
class ModeState:
    think: bool = True
    rag: bool = True
    ctx: bool = False
    topk: int = 5
    source: str | None = None
    provider: str = "local"
    backend: str = "hacker_lm"
    model: str = "Hermes-4-14B (Q6_K, llama-server)"
    think_control: str = "detecting"

    def toggle(self, field_name: str) -> bool:
        current = getattr(self, field_name)
        updated = not current
        setattr(self, field_name, updated)
        return updated

    def set_flag(self, field_name: str, value: bool) -> bool:
        setattr(self, field_name, value)
        return value

    def set_topk(self, value: int) -> int:
        if value < 1 or value > 20:
            raise ValueError("TOPK must stay between 1 and 20.")
        self.topk = value
        return value

    def set_source(self, value: str | None) -> str | None:
        if value is None:
            self.source = None
            return None
        if value not in VALID_SOURCE_FILTERS:
            raise ValueError(f"source must be one of {', '.join(VALID_SOURCE_FILTERS)} or none")
        self.source = value
        return value

    def snapshot(self) -> str:
        return (
            f"THINK={'ON' if self.think else 'OFF'}  "
            f"RAG={'ON' if self.rag else 'OFF'}  "
            f"CTX={'ON' if self.ctx else 'OFF'}  "
            f"TOPK={self.topk}  "
            f"SOURCE={(self.source or 'any').upper()}  "
            f"THINK_CTRL={self.think_control.upper()}"
        )


@dataclass(slots=True)
class ConversationState:
    id: str = field(default_factory=lambda: uuid4().hex)
    messages: list[ChatMessage] = field(default_factory=list)

    def add(self, message: ChatMessage) -> ChatMessage:
        self.messages.append(message)
        return message

    def model_history(self) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        for message in self.messages:
            if message.kind == MessageKind.USER:
                history.append({"role": "user", "content": message.text})
            elif message.kind == MessageKind.ASSISTANT:
                history.append({"role": "assistant", "content": message.text})
        return history


@dataclass(slots=True)
class CommandResult:
    feedback: str
    exit_requested: bool = False


def apply_slash_command(raw: str, modes: ModeState) -> CommandResult:
    parts = raw.strip().split()
    if not parts:
        raise ValueError("Empty command.")

    command = parts[0].lower()
    arg = parts[1].lower() if len(parts) > 1 else ""

    if command == "/help":
        return CommandResult(HELP_TEXT)
    if command in {"/quit", "/exit"}:
        return CommandResult("Closing session.", exit_requested=True)
    if command == "/state":
        return CommandResult(modes.snapshot())
    if command in {"/think", "/rag", "/ctx", "/context"}:
        if arg not in {"on", "off"}:
            raise ValueError(f"Usage: {command} on|off")
        field_name = "ctx" if command in {"/ctx", "/context"} else command.lstrip("/")
        modes.set_flag(field_name, arg == "on")
        return CommandResult(f"{field_name.upper()} set to {arg.upper()}.")
    if command == "/topk":
        if len(parts) != 2:
            raise ValueError("Usage: /topk <n>")
        try:
            value = int(parts[1])
        except ValueError as error:
            raise ValueError("Usage: /topk <n>") from error
        modes.set_topk(value)
        return CommandResult(f"TOPK set to {value}.")
    if command == "/source":
        if len(parts) != 2:
            raise ValueError(f"Usage: /source <{'|'.join(VALID_SOURCE_FILTERS)}|none>")
        raw_value = parts[1].lower()
        if raw_value == "none":
            modes.set_source(None)
            return CommandResult("SOURCE filter cleared.")
        modes.set_source(raw_value)
        return CommandResult(f"SOURCE set to {raw_value}.")

    raise ValueError(f"Unknown command: {command}. Try /help.")
