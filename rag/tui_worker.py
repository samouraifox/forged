from __future__ import annotations

import argparse
import json
import sys

from .config import V2_COLLECTION, V2_DB_PATH
from .runtime import ensure_ollama_running
from .service import QueryConfig, QueryEventType, RetrieveService


def emit(event_type: str, text: str = "", *, request_id: str | None = None, **extra: object) -> None:
    payload: dict[str, object] = {"type": event_type}
    if text:
        payload["text"] = text
    if request_id:
        payload["request_id"] = request_id
    payload.update(extra)
    print(json.dumps(payload), flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Structured TUI worker for hacker_lm.")
    parser.add_argument("--db", default=None)
    parser.add_argument("--collection", default=None)
    return parser


def startup(service: RetrieveService) -> None:
    emit("status", "checking ollama runtime")
    ensure_ollama_running(status_callback=lambda message: emit("status", message))
    for event in service.initialize():
        emit(event.type.value, event.text)
    emit(
        "ready",
        provider=service.provider,
        backend=service.backend_name,
        model=service.model_name,
        think_control=service.think_control,
    )


def handle_request(service: RetrieveService, payload: dict[str, object]) -> None:
    request_id = str(payload.get("request_id", ""))
    try:
        config = QueryConfig.from_mapping(dict(payload.get("modes", {})))
    except Exception as error:
        emit("error", str(error), request_id=request_id)
        emit("done", request_id=request_id)
        return

    prompt = str(payload.get("prompt", ""))
    raw_history = payload.get("history")
    history = raw_history if isinstance(raw_history, list) else None
    try:
        for event in service.stream_query(prompt, config, history=history):
            emit(event.type.value, event.text, request_id=request_id)
    except Exception as error:
        emit("error", f"{type(error).__name__}: {error}", request_id=request_id)
        emit("done", request_id=request_id)


def main() -> int:
    args = build_parser().parse_args()
    db_path = args.db or V2_DB_PATH
    collection = args.collection or V2_COLLECTION
    service = RetrieveService(db_path=db_path, collection=collection)

    try:
        startup(service)
    except Exception as error:
        emit("error", str(error), fatal=True)
        return 1

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            emit("error", f"protocol error: {error}")
            continue

        request_type = payload.get("type")
        if request_type == "shutdown":
            break
        if request_type != "request":
            emit("error", f"unknown request type: {request_type}")
            continue
        handle_request(service, payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
