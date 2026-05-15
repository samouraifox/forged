"""Textual chat frontend shell for a local LLM backend."""

__all__ = ["LocalChatApp"]


def __getattr__(name: str):
    if name == "LocalChatApp":
        from .app import LocalChatApp

        return LocalChatApp
    raise AttributeError(name)
