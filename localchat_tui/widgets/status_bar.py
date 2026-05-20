from __future__ import annotations

import os
import time
from pathlib import Path

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from ..backend import BackendDescriptor
from ..state import ModeState

try:
    import psutil  # type: ignore

    _HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore
    _HAS_PSUTIL = False


def _read_meminfo_used_gb() -> float | None:
    """Fallback: parse /proc/meminfo to get used RAM in GiB."""
    try:
        kb: dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as fh:
            for line in fh:
                if ":" not in line:
                    continue
                key, _, rest = line.partition(":")
                value_kb = rest.strip().split()[0]
                try:
                    kb[key.strip()] = int(value_kb)
                except ValueError:
                    continue
        total = kb.get("MemTotal")
        available = kb.get("MemAvailable")
        if total is None or available is None:
            return None
        used_kb = total - available
        return used_kb / 1024 / 1024
    except OSError:
        return None


def _process_start_epoch(pid: int) -> float | None:
    """Fallback: read process start time (clock ticks since boot) and compute epoch."""
    try:
        with open(f"/proc/{pid}/stat", "rb") as fh:
            data = fh.read()
        rparen = data.rfind(b")")
        if rparen == -1:
            return None
        fields = data[rparen + 2 :].split()
        # field 22 (1-indexed) of /proc/[pid]/stat is starttime in clock ticks
        # after the comm field which we just skipped past — that is index 19 in
        # the post-comm split (22 - 2 - 1).
        if len(fields) < 20:
            return None
        starttime_ticks = int(fields[19])
        clk_tck = os.sysconf("SC_CLK_TCK")
        with open("/proc/uptime", "r", encoding="utf-8") as fh:
            uptime = float(fh.read().split()[0])
        boot_epoch = time.time() - uptime
        return boot_epoch + (starttime_ticks / clk_tck)
    except (OSError, ValueError):
        return None


def _format_uptime(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours >= 100:
        return f"{hours}h{minutes:02d}m"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class StatusBar(Widget):
    """Bottom status bar: backend identity line + live mode/system line."""

    def __init__(
        self,
        descriptor: BackendDescriptor,
        modes: ModeState,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.descriptor = descriptor
        self.modes = modes
        self._start_epoch: float | None = None
        if _HAS_PSUTIL and psutil is not None:
            try:
                self._start_epoch = psutil.Process(os.getpid()).create_time()
            except Exception:
                self._start_epoch = None
        if self._start_epoch is None:
            self._start_epoch = _process_start_epoch(os.getpid()) or time.time()

    def compose(self) -> ComposeResult:
        yield Static("", id="status-line-1")
        yield Static("", id="status-line-2")

    def on_mount(self) -> None:
        self.refresh_status()
        self.set_interval(4.0, self.refresh_status)

    def set_descriptor(self, descriptor: BackendDescriptor) -> None:
        self.descriptor = descriptor
        if self.is_mounted:
            self.refresh_status()

    def set_modes(self, modes: ModeState) -> None:
        self.modes = modes
        if self.is_mounted:
            self.refresh_status()

    def refresh_status(self) -> None:
        if not self.is_mounted:
            return
        self.query_one("#status-line-1", Static).update(self._render_line_1())
        self.query_one("#status-line-2", Static).update(self._render_line_2())

    def _render_line_1(self) -> str:
        model = self.descriptor.model.upper()
        provider = self.descriptor.provider
        backend = self.descriptor.name
        think_ctrl = self.descriptor.think_control
        return (
            f"[#39ff14]●[/] [b]{model}[/b]   "
            f"[#5a8060]·[/]   [#ff39c6]{provider}[/]   "
            f"[#5a8060]·[/]   [#39c6ff]{backend}[/]   "
            f"[#5a8060]·[/]   think:{think_ctrl}"
        )

    def _render_line_2(self) -> str:
        modes = self.modes

        def chip(label: str, on: bool) -> str:
            if on:
                return f"[#39ff14 b]{label} on[/]"
            return f"[#3a5a40]{label} off[/]"

        ram = self._format_ram()
        uptime = self._format_uptime()
        source = (modes.source or "any").upper()

        return (
            f"{chip('THINK', modes.think)}  "
            f"{chip('RAG', modes.rag)}  "
            f"{chip('CTX', modes.ctx)}  "
            f"[#5a8060]·[/] [#39c6ff]TOPK[/] [#c8f5d4]{modes.topk}[/]  "
            f"[#5a8060]·[/] [#39c6ff]SRC[/] [#c8f5d4]{source}[/]  "
            f"[#5a8060]│[/]  "
            f"[#39c6ff]RAM[/] [#c8f5d4]{ram}[/]  "
            f"[#5a8060]·[/] [#39c6ff]UP[/] [#c8f5d4]{uptime}[/]"
        )

    def _format_ram(self) -> str:
        if _HAS_PSUTIL and psutil is not None:
            try:
                vm = psutil.virtual_memory()
                used_gb = (vm.total - vm.available) / (1024 ** 3)
                total_gb = vm.total / (1024 ** 3)
                return f"{used_gb:.1f}/{total_gb:.0f}G"
            except Exception:
                pass
        used = _read_meminfo_used_gb()
        if used is None:
            return "n/a"
        return f"{used:.1f}G"

    def _format_uptime(self) -> str:
        if self._start_epoch is None:
            return "n/a"
        return _format_uptime(time.time() - self._start_epoch)
