"""Entry point for the installed ``sesame-wake`` console script."""

from sesame_wake.config import load_config
from sesame_wake.listener import run_listener
from sesame_wake.session import SessionManager


def main() -> None:
    config = load_config()
    session = SessionManager(config)
    try:
        run_listener(session, config)
    finally:
        session.shutdown()


if __name__ == "__main__":
    main()
