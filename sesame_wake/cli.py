"""Entry point for the installed ``sesame-wake`` console script."""

import argparse

from sesame_wake.config import load_config
from sesame_wake.listener import run_listener
from sesame_wake.session import SessionManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wake-word launcher for Sesame.")
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Run the original log-only listener instead of the terminal UI.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()

    if not args.plain:
        from sesame_wake.tui import run_tui

        run_tui(config)
        return

    session = SessionManager(config)
    try:
        run_listener(session, config)
    finally:
        session.shutdown()


if __name__ == "__main__":
    main()
