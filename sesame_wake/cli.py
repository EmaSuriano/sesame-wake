"""Entry point for the installed ``sesame-wake`` console script."""

from sesame_wake.config import validate_config
from sesame_wake.listener import run_listener
from sesame_wake.session import SessionManager


def main() -> None:
    validate_config()
    session = SessionManager()
    try:
        run_listener(session)
    finally:
        session.shutdown()


if __name__ == "__main__":
    main()
