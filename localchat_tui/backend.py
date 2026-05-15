from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from uuid import uuid4

from .state import ConversationState, ModeState


@dataclass(frozen=True, slots=True)
class BackendDescriptor:
    provider: str
    name: str
    model: str
    think_control: str = "detecting"


class StreamChannel(str, Enum):
    STATUS = "status"
    RETRIEVED_CONTEXT = "retrieved_context"
    THINKING = "thinking"
    ANSWER_CHUNK = "answer_chunk"
    ERROR = "error"
    DONE = "done"


@dataclass(frozen=True, slots=True)
class StreamEvent:
    channel: StreamChannel
    text: str


class ChatBackendAdapter(ABC):
    descriptor: BackendDescriptor

    async def startup(self) -> AsyncIterator[StreamEvent]:
        if False:
            yield StreamEvent(StreamChannel.STATUS, "")

    @abstractmethod
    async def stream_reply(
        self,
        prompt: str,
        conversation: ConversationState,
        modes: ModeState,
    ) -> AsyncIterator[StreamEvent]:
        """Yield streamed backend events for the active prompt."""

    async def aclose(self) -> None:
        return None


class HackerLMBackendAdapter(ChatBackendAdapter):
    def __init__(self, project_root: Path | None = None) -> None:
        root = project_root or Path(__file__).resolve().parents[1]
        self.project_root = root
        self.worker_python = root / "rag" / "venv" / "bin" / "python"
        self.worker_db = root / "rag" / "chroma_db"
        self.descriptor = BackendDescriptor(
            provider="local",
            name="hacker_lm",
            model="DeepSeek-R1 abliterated (starting…)",
            think_control="detecting",
        )
        self._proc: asyncio.subprocess.Process | None = None
        self._ready = False
        self._startup_lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()
        self._stderr_task: asyncio.Task[None] | None = None
        self._stderr_tail: deque[str] = deque(maxlen=40)

    async def startup(self) -> AsyncIterator[StreamEvent]:
        async for event in self._ensure_process():
            yield event

    async def stream_reply(
        self,
        prompt: str,
        conversation: ConversationState,
        modes: ModeState,
    ) -> AsyncIterator[StreamEvent]:
        async for event in self._ensure_process():
            yield event

        request_id = uuid4().hex
        payload = {
            "type": "request",
            "request_id": request_id,
            "prompt": prompt,
            "history": conversation.model_history(),
            "modes": {
                "think": modes.think,
                "rag": modes.rag,
                "topk": modes.topk,
                "source": modes.source,
                "show_context": modes.ctx,
            },
        }

        async with self._request_lock:
            await self._send_payload(payload)
            try:
                async for event in self._stream_request_events(request_id):
                    yield event
            except Exception as error:
                yield StreamEvent(StreamChannel.ERROR, str(error))

    async def aclose(self) -> None:
        proc = self._proc
        self._proc = None
        self._ready = False
        if proc is None:
            return

        if proc.returncode is None and proc.stdin is not None:
            try:
                await self._send_payload({"type": "shutdown"}, proc=proc)
            except Exception:
                pass

        if proc.returncode is None:
            try:
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()

        if self._stderr_task is not None:
            try:
                await self._stderr_task
            except Exception:
                pass
            self._stderr_task = None

    async def _ensure_process(self) -> AsyncIterator[StreamEvent]:
        async with self._startup_lock:
            if self._process_alive() and self._ready:
                return

            await self.aclose()
            if not self.worker_python.exists():
                raise RuntimeError(f"backend runtime not found: {self.worker_python}")
            if not self.worker_db.exists():
                raise RuntimeError(f"backend database not found: {self.worker_db}")

            yield StreamEvent(StreamChannel.STATUS, "booting real hacker_lm backend")
            self._proc = await asyncio.create_subprocess_exec(
                str(self.worker_python),
                "-u",
                "-m",
                "rag.tui_worker",
                "--db",
                str(self.worker_db),
                cwd=str(self.project_root),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._stderr_tail.clear()
            self._stderr_task = asyncio.create_task(self._drain_stderr())

            while True:
                payload = await self._read_payload()
                payload_type = str(payload.get("type", ""))
                if payload_type == "ready":
                    self.descriptor = BackendDescriptor(
                        provider=str(payload.get("provider", "local")),
                        name=str(payload.get("backend", "hacker_lm")),
                        model=str(payload.get("model", "unknown")),
                        think_control=str(payload.get("think_control", "unknown")),
                    )
                    self._ready = True
                    return
                event = self._payload_to_event(payload)
                if event is None:
                    continue
                if event.channel == StreamChannel.ERROR:
                    await self.aclose()
                    raise RuntimeError(event.text)
                yield event

    async def _stream_request_events(self, request_id: str) -> AsyncIterator[StreamEvent]:
        while True:
            payload = await self._read_payload()
            payload_type = str(payload.get("type", ""))
            payload_request_id = str(payload.get("request_id", ""))
            if payload_type == "ready":
                self.descriptor = BackendDescriptor(
                    provider=str(payload.get("provider", "local")),
                    name=str(payload.get("backend", "hacker_lm")),
                    model=str(payload.get("model", "unknown")),
                    think_control=str(payload.get("think_control", "unknown")),
                )
                self._ready = True
                continue
            if payload_request_id and payload_request_id != request_id:
                continue

            event = self._payload_to_event(payload)
            if event is None:
                continue
            yield event
            if event.channel == StreamChannel.DONE:
                break

    async def _send_payload(self, payload: dict[str, object], *, proc: asyncio.subprocess.Process | None = None) -> None:
        process = proc or self._require_process()
        if process.stdin is None:
            raise RuntimeError("backend stdin is not available")
        process.stdin.write(json.dumps(payload).encode("utf-8") + b"\n")
        await process.stdin.drain()

    async def _read_payload(self) -> dict[str, object]:
        proc = self._require_process()
        if proc.stdout is None:
            raise RuntimeError("backend stdout is not available")

        line = await proc.stdout.readline()
        if not line:
            await proc.wait()
            stderr = "\n".join(self._stderr_tail).strip()
            message = f"backend worker exited with code {proc.returncode}"
            if stderr:
                message = f"{message}\n{stderr}"
            raise RuntimeError(message)

        text = line.decode("utf-8", errors="replace").strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"backend emitted invalid JSON: {text}") from error
        return payload

    async def _drain_stderr(self) -> None:
        proc = self._proc
        if proc is None or proc.stderr is None:
            return
        while True:
            line = await proc.stderr.readline()
            if not line:
                return
            self._stderr_tail.append(line.decode("utf-8", errors="replace").rstrip())

    def _payload_to_event(self, payload: dict[str, object]) -> StreamEvent | None:
        payload_type = str(payload.get("type", ""))
        text = str(payload.get("text", ""))
        mapping = {
            "status": StreamChannel.STATUS,
            "retrieved_context": StreamChannel.RETRIEVED_CONTEXT,
            "thinking": StreamChannel.THINKING,
            "answer_chunk": StreamChannel.ANSWER_CHUNK,
            "error": StreamChannel.ERROR,
            "done": StreamChannel.DONE,
        }
        channel = mapping.get(payload_type)
        if channel is None:
            return None
        return StreamEvent(channel, text)

    def _require_process(self) -> asyncio.subprocess.Process:
        if self._proc is None:
            raise RuntimeError("backend process is not running")
        return self._proc

    def _process_alive(self) -> bool:
        return self._proc is not None and self._proc.returncode is None
