"""Selenium session lifecycle for Sesame."""

import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from sesame_wake.config import (
    AGENT_NAME,
    AGENT_SELECTOR,
    BUTTON_TIMEOUT,
    OPEN_RETRIES,
    RETRY_DELAY,
    TARGET_URL,
    AppConfig,
)
from sesame_wake.logging_setup import log
from sesame_wake.sounds import play_sound_async


class SessionManager:
    """
    Owns the Selenium driver lifecycle and tracks whether Sesame is active.

    Having a single class responsible for both avoids the global-variable
    state-sync bug where `session_active` and `driver` could disagree.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._driver: webdriver.Chrome | None = None

    def _build_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument(f"--user-data-dir={self._config.selenium_profile}")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        return webdriver.Chrome(options=options)

    def _is_driver_alive(self) -> bool:
        """Probe the browser with a JS round-trip — more reliable than current_url."""
        if self._driver is None:
            return False
        try:
            self._driver.execute_script("return true")
            return True
        except WebDriverException:
            return False

    def _ensure_driver(self) -> webdriver.Chrome:
        if not self._is_driver_alive():
            log.debug("Browser not alive — creating new driver.")
            self._driver = self._build_driver()
        assert self._driver is not None
        return self._driver

    @property
    def is_active(self) -> bool:
        """
        Ground-truth session state: active only if the driver is alive.
        Automatically recovers if the user manually closes the browser.
        """
        alive = self._is_driver_alive()
        if not alive and self._driver is not None:
            log.info("Browser was closed externally — resetting session state.")
            self._driver = None
        return alive

    def open(self) -> bool:
        """
        Navigate to Sesame and click the agent button.
        Retries up to OPEN_RETRIES times on failure.
        Returns True on success, False if all retries are exhausted.
        """
        for attempt in range(1, OPEN_RETRIES + 1):
            try:
                log.info("Opening Sesame (attempt %d/%d)...", attempt, OPEN_RETRIES)
                driver = self._ensure_driver()
                driver.get(TARGET_URL)

                button = WebDriverWait(driver, BUTTON_TIMEOUT).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, AGENT_SELECTOR))
                )
                time.sleep(0.5)
                button.click()
                log.info("✅ Clicked %s!", AGENT_NAME)
                return True

            except Exception as e:
                log.warning("Open attempt %d failed: %s", attempt, e)
                self._quit_driver()
                if attempt < OPEN_RETRIES:
                    time.sleep(RETRY_DELAY)

        log.error("All %d open attempts failed.", OPEN_RETRIES)
        return False

    def close(self) -> None:
        """Quit the browser and reset state."""
        if not self._is_driver_alive():
            log.warning("No active Sesame browser to close.")
            return
        log.info("Closing Sesame...")
        self._quit_driver()
        log.info("✅ Sesame closed.")

    def toggle(self) -> None:
        """Open if inactive, close if active."""
        if self.is_active:
            play_sound_async(self._config.end_sound)
            self.close()
        else:
            play_sound_async(self._config.start_sound)
            success = self.open()
            if not success:
                play_sound_async(self._config.end_sound)

    def shutdown(self) -> None:
        """Called on exit to ensure clean browser teardown."""
        if self._is_driver_alive():
            log.info("Shutting down browser...")
            self._quit_driver()

    def _quit_driver(self) -> None:
        try:
            if self._driver:
                self._driver.quit()
        except Exception as e:
            log.debug("Error quitting driver (safe to ignore): %s", e)
        finally:
            self._driver = None
