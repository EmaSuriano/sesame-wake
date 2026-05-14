"""Textual terminal UI for sesame-wake."""

from __future__ import annotations

import logging
from threading import Event, Thread
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, ProgressBar, RichLog, Static

from sesame_wake.config import THRESHOLD, AppConfig
from sesame_wake.listener import ListenerEvent, run_listener
from sesame_wake.logging_setup import log
from sesame_wake.session import SessionManager


class TextualLogHandler(logging.Handler):
    def __init__(self, app: SesameWakeApp) -> None:
        super().__init__(level=logging.INFO)
        self._app = app

    def emit(self, record: logging.LogRecord) -> None:
        self._app.call_from_thread(self._app.add_log, self.format(record))


class SesameWakeApp(App[None]):
    """Interactive Textual dashboard for the wake listener."""

    CSS = """
    Screen {
        background: $surface;
    }

    #layout {
        height: 1fr;
        padding: 1 2;
    }

    .panel {
        border: solid $primary;
        padding: 1 2;
        margin-bottom: 1;
    }

    #status-panel {
        height: 8;
    }

    #score-panel {
        height: 6;
    }

    .meter {
        width: 1fr;
        height: 4;
    }

    .meter:first-child {
        margin-right: 2;
    }

    #events-panel {
        height: 1fr;
    }

    .label {
        width: 14;
        color: $text-muted;
    }

    .value {
        width: 1fr;
    }

    #browser.open {
        color: $success;
        text-style: bold;
    }

    #browser.closed {
        color: $error;
        text-style: bold;
    }

    #events {
        height: 1fr;
        border: none;
    }
    """

    BINDINGS: ClassVar = [
        Binding("t", "toggle", "Toggle Sesame"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.session = SessionManager(config)
        self.stop_event = Event()
        self.listener: Thread | None = None
        self.log_handler: TextualLogHandler | None = None
        self.removed_log_handlers: list[logging.Handler] = []
        self.busy = False
        self.status_check_running = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="layout"):
            with Vertical(classes="panel", id="status-panel"):
                yield Static("Starting listener", id="status")
                yield self._row("Browser", Static("unknown", id="browser"))
                yield self._row("Wake model", Static(self.config.wake_model_path.name))
                yield self._row("Profile", Static(self.config.selenium_profile))
            with Vertical(classes="panel", id="score-panel"), Horizontal():
                with Vertical(classes="meter"):
                    yield Static(
                        f"Wake score 0.00  threshold {THRESHOLD:.2f}",
                        id="score-label",
                    )
                    yield ProgressBar(total=100, show_eta=False, id="score")
                with Vertical(classes="meter"):
                    yield Static("Mic level 0%", id="mic-label")
                    yield ProgressBar(total=100, show_eta=False, id="mic-level")
            with Vertical(classes="panel", id="events-panel"):
                yield Static("Recent events")
                yield RichLog(id="events", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._install_log_capture()
        self.listener = Thread(target=self._listener_worker, name="sesame-listener", daemon=True)
        self.listener.start()
        self.set_interval(1.5, self.refresh_browser_status)

    def on_unmount(self) -> None:
        self.stop_event.set()
        self.session.shutdown()
        if self.listener:
            self.listener.join(timeout=2)
        self._restore_log_capture()

    def action_toggle(self) -> None:
        if self.busy:
            return
        self.busy = True
        self.set_status("Toggling Sesame")
        Thread(target=self._toggle_worker, name="sesame-manual-toggle", daemon=True).start()

    def refresh_browser_status(self) -> None:
        if self.busy or self.status_check_running:
            return
        self.status_check_running = True
        Thread(target=self._browser_status_worker, name="sesame-status-check", daemon=True).start()

    def set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def set_browser_status(self, status: str) -> None:
        browser = self.query_one("#browser", Static)
        browser.update(status)
        browser.remove_class("open", "closed")
        browser.add_class(status)

    def set_score(self, score: float) -> None:
        self.query_one("#score", ProgressBar).update(progress=min(100, max(0, score * 100)))
        self.query_one("#score-label", Static).update(
            f"Wake score {score:.2f}  threshold {THRESHOLD:.2f}"
        )

    def set_input_level(self, level: float) -> None:
        percent = min(100, max(0, round(level * 100)))
        self.query_one("#mic-level", ProgressBar).update(progress=percent)
        self.query_one("#mic-label", Static).update(f"Mic level {percent}%")

    def add_log(self, message: str) -> None:
        self.query_one("#events", RichLog).write(message)

    def handle_listener_event(self, event: ListenerEvent) -> None:
        self.call_from_thread(self._apply_listener_event, event)

    def _browser_status_worker(self) -> None:
        try:
            status = "open" if self.session.is_active else "closed"
            self.call_from_thread(self.set_browser_status, status)
        finally:
            self.status_check_running = False

    def _listener_worker(self) -> None:
        try:
            run_listener(
                self.session,
                self.config,
                events=self.handle_listener_event,
                stop_event=self.stop_event,
            )
        except Exception as exc:
            log.exception("Listener stopped unexpectedly")
            self.call_from_thread(self.set_status, "Listener stopped unexpectedly")
            self.call_from_thread(self.add_log, f"[red]ERROR:[/] {exc}")
        finally:
            self.call_from_thread(self.add_log, "Listener stopped")

    def _toggle_worker(self) -> None:
        try:
            action = self.session.toggle()
            self.call_from_thread(self.set_status, "Manual toggle finished")
            if action == "OPEN":
                self.call_from_thread(self.set_browser_status, "open")
            elif action in {"CLOSE", "OPEN_FAILED"}:
                self.call_from_thread(self.set_browser_status, "closed")
            self.call_from_thread(self.add_log, "Manual toggle finished")
        except Exception as exc:
            log.exception("Manual toggle failed")
            self.call_from_thread(self.set_status, "Manual toggle failed")
            self.call_from_thread(self.add_log, f"[red]ERROR:[/] {exc}")
        finally:
            self.busy = False

    def _apply_listener_event(self, event: ListenerEvent) -> None:
        if event.kind == "ready":
            self.set_status(event.message)
            self.add_log(event.message)
        elif event.kind == "score" and event.score is not None:
            self.set_score(event.score)
        elif event.kind == "input_level" and event.score is not None:
            self.set_input_level(event.score)
        elif event.kind == "detected" and event.score is not None:
            self.busy = True
            self.set_status("Wake detected")
            self.add_log(f"{event.message} ({event.score:.2f})")
        elif event.kind == "toggled":
            self.busy = False
            self.set_status(event.message)
            if event.action == "OPEN":
                self.set_browser_status("open")
            elif event.action in {"CLOSE", "OPEN_FAILED"}:
                self.set_browser_status("closed")
            self.add_log(event.message)
        elif event.kind == "microphone":
            self.set_status(event.message)
            self.add_log(f"[yellow]{event.message}[/]")

    def _install_log_capture(self) -> None:
        handler = TextualLogHandler(self)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

        self.removed_log_handlers = [
            handler
            for handler in log.handlers
            if isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, logging.FileHandler)
            and not isinstance(handler, TextualLogHandler)
        ]
        for removed in self.removed_log_handlers:
            log.removeHandler(removed)
        log.addHandler(handler)
        self.log_handler = handler

    def _restore_log_capture(self) -> None:
        if self.log_handler:
            log.removeHandler(self.log_handler)
            self.log_handler = None
        for removed in self.removed_log_handlers:
            log.addHandler(removed)
        self.removed_log_handlers = []

    @staticmethod
    def _row(label: str, value: Static) -> Horizontal:
        return Horizontal(Static(label, classes="label"), value, classes="row")


def run_tui(config: AppConfig) -> None:
    """Run the Textual UI."""
    SesameWakeApp(config).run()
