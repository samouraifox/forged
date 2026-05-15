from __future__ import annotations

from .app import LocalChatApp
from .backend import HackerLMBackendAdapter


def main() -> None:
    LocalChatApp(adapter=HackerLMBackendAdapter()).run()


if __name__ == "__main__":
    main()
