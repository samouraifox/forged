from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
import re

OLLAMA_LOG = Path("/tmp/ollama.log")
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_PORT = 11434
OLLAMA_READY_TIMEOUT_S = 15.0
OLLAMA_SHUTDOWN_TIMEOUT_S = 10.0
OLLAMA_POLL_INTERVAL_S = 0.5
LISTEN_STATE = "0A"
SOCKET_LINK_RE = re.compile(r"socket:\[(\d+)\]")


def ensure_ollama_running(status_callback: Callable[[str], None] | None = None) -> None:
    emit = status_callback or (lambda _message: None)

    existing_pids = _ollama_pids()
    stale_pids: set[int] = set()

    if existing_pids:
        if all(_has_flash_attention_disabled(pid) for pid in existing_pids):
            emit("ollama already running; verifying listener and API")
            reason = _wait_for_ollama_ready(expected_pids=set(existing_pids))
            if reason is None:
                emit("ollama runtime ready")
                return
            emit(f"existing ollama failed verification ({reason}); restarting")
        else:
            emit("ollama running without FLASH_ATTENTION=0; restarting")
        stale_pids = set(existing_pids)
        remaining = _stop_processes(existing_pids)
        if remaining:
            raise RuntimeError(
                f"failed to stop existing ollama process(es): {_format_pid_list(remaining)}"
            )

    try:
        emit(f"starting ollama (FLASH_ATTENTION=0) -> {OLLAMA_LOG}")
        started_pid = _start_ollama()
    except FileNotFoundError as error:
        raise RuntimeError("`ollama` is not installed or not on PATH.") from error

    reason = _wait_for_ollama_ready(expected_pids={started_pid}, stale_pids=stale_pids)
    if reason is not None:
        raise RuntimeError(f"ollama failed to start ({reason}) — see {OLLAMA_LOG}")

    emit("ollama runtime ready")


def _ollama_pids() -> list[int]:
    result = subprocess.run(
        ["pgrep", "-x", "ollama"],
        check=False,
        capture_output=True,
        text=True,
    )
    return [int(line) for line in result.stdout.splitlines() if line.strip().isdigit()]


def _has_flash_attention_disabled(pid: int) -> bool:
    try:
        environ = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return False
    return b"OLLAMA_FLASH_ATTENTION=0\x00" in environ or environ.endswith(b"OLLAMA_FLASH_ATTENTION=0")


def _stop_processes(pids: list[int]) -> list[int]:
    targets = sorted(set(pid for pid in pids if _is_ollama_process(pid)))
    for pid in targets:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            continue
    return _wait_for_shutdown(targets)


def _wait_for_shutdown(pids: list[int], timeout_s: float = OLLAMA_SHUTDOWN_TIMEOUT_S) -> list[int]:
    if not pids:
        return []

    deadline = time.monotonic() + timeout_s
    remaining = _running_target_pids(pids)
    while remaining and time.monotonic() < deadline:
        time.sleep(OLLAMA_POLL_INTERVAL_S)
        remaining = _running_target_pids(pids)
    return remaining


def _running_target_pids(pids: list[int]) -> list[int]:
    return [pid for pid in pids if _is_ollama_process(pid)]


def _is_ollama_process(pid: int) -> bool:
    try:
        return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip() == "ollama"
    except OSError:
        return False


def _start_ollama() -> int:
    env = os.environ.copy()
    env["OLLAMA_FLASH_ATTENTION"] = "0"
    with OLLAMA_LOG.open("ab") as log_handle:
        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    return process.pid


def _wait_for_ollama_ready(
    *,
    expected_pids: set[int] | None = None,
    stale_pids: set[int] | None = None,
    timeout_s: float = OLLAMA_READY_TIMEOUT_S,
) -> str | None:
    deadline = time.monotonic() + timeout_s
    last_reason = "ollama API is not responding"
    while time.monotonic() < deadline:
        last_reason = _verify_ollama_runtime(expected_pids=expected_pids, stale_pids=stale_pids)
        if last_reason is None:
            return None
        time.sleep(OLLAMA_POLL_INTERVAL_S)
    return last_reason


def _verify_ollama_runtime(
    *,
    expected_pids: set[int] | None = None,
    stale_pids: set[int] | None = None,
) -> str | None:
    current_pids = _ollama_pids()
    if not current_pids:
        return "no ollama server process is running"
    if expected_pids is not None and not set(current_pids).intersection(expected_pids):
        return "expected ollama server PID is no longer running"
    if not all(_has_flash_attention_disabled(pid) for pid in current_pids):
        return "one or more ollama server processes are missing OLLAMA_FLASH_ATTENTION=0"

    owner_pids = _port_owner_pids(OLLAMA_PORT, candidate_pids=current_pids)
    if not owner_pids:
        return f":{OLLAMA_PORT} is not owned by an ollama server process"
    if stale_pids and set(owner_pids).intersection(stale_pids):
        return f"stale ollama PID still owns :{OLLAMA_PORT}"
    if expected_pids is not None and not set(owner_pids).intersection(expected_pids):
        return f"expected ollama server PID does not own :{OLLAMA_PORT}"
    if not all(_has_flash_attention_disabled(pid) for pid in owner_pids):
        return f"the serving ollama process on :{OLLAMA_PORT} is missing OLLAMA_FLASH_ATTENTION=0"
    if not _ollama_api_ready():
        return "ollama API is not responding on /api/tags"
    return None


def _port_owner_pids(port: int, *, candidate_pids: list[int] | None = None) -> list[int]:
    listener_inodes = _listener_inodes(port)
    if not listener_inodes:
        return []

    owners: list[int] = []
    for pid in candidate_pids or _ollama_pids():
        if listener_inodes.intersection(_pid_socket_inodes(pid)):
            owners.append(pid)
    return owners


def _listener_inodes(port: int) -> set[str]:
    port_hex = f"{port:04X}"
    inodes: set[str] = set()
    for net_file in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lines = Path(net_file).read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 10:
                continue
            local_address = parts[1]
            state = parts[3]
            inode = parts[9]
            if state != LISTEN_STATE or ":" not in local_address:
                continue
            _, local_port = local_address.rsplit(":", 1)
            if local_port.upper() == port_hex:
                inodes.add(inode)
    return inodes


def _pid_socket_inodes(pid: int) -> set[str]:
    fd_dir = Path(f"/proc/{pid}/fd")
    try:
        fds = list(fd_dir.iterdir())
    except OSError:
        return set()

    inodes: set[str] = set()
    for fd_path in fds:
        try:
            target = str(fd_path.readlink())
        except OSError:
            continue
        match = SOCKET_LINK_RE.fullmatch(target)
        if match:
            inodes.add(match.group(1))
    return inodes


def _format_pid_list(pids: list[int]) -> str:
    return ", ".join(str(pid) for pid in sorted(set(pids)))


def _ollama_api_ready() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=1.0) as response:
            return 200 <= response.status < 300
    except (OSError, urllib.error.URLError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime helpers for hacker_lm.")
    parser.add_argument("--ensure-ollama", action="store_true", help="Start Ollama if needed.")
    args = parser.parse_args()

    if args.ensure_ollama:
        try:
            ensure_ollama_running(status_callback=lambda message: print(f"[hacker_lm] {message}", flush=True))
        except RuntimeError as error:
            print(f"[hacker_lm] {error}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
