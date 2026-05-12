# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openwakeword",
#   "pyaudio",
#   "numpy",
#   "selenium",
#   "python-dotenv",
# ]
# ///

"""
Wake word launcher for Sesame (macOS, dedicated profile)

Wake words:
- "hey jarvis"     -> Opens Sesame + clicks the agent button
- "goodbye jarvis" -> Closes the Sesame browser session

Configuration:
- Copy .env.example to .env and set SELENIUM_PROFILE
- Place your custom model at ./models/goodbye_jarvis.onnx
"""

import os
import time
import subprocess

import numpy as np
import pyaudio
import openwakeword
from dotenv import load_dotenv
from openwakeword.model import Model
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ── Config ─────────────────────────────────────────────────────────────
OPEN_WORD   = "hey_jarvis"
CLOSE_WORD  = "goodbye_jarvis"
CLOSE_MODEL = "./models/goodbye_jarvis.onnx"

AGENT_NAME     = "Miles"  # possible agents: Miles or Maya
AGENT_SELECTOR = f'[aria-label="{AGENT_NAME}"]'  # derived from AGENT_NAME

TARGET_URL     = "https://app.sesame.com/"
THRESHOLD      = 0.5
BUTTON_TIMEOUT = 15
CHUNK_SIZE     = 1280
SAMPLE_RATE    = 16000

load_dotenv()
SELENIUM_PROFILE = os.getenv("SELENIUM_PROFILE")
# ───────────────────────────────────────────────────────────────────────


def validate_config() -> None:
    """Fail fast with clear messages if the environment is misconfigured."""
    if not SELENIUM_PROFILE:
        raise ValueError("SELENIUM_PROFILE is not set in .env")
    if not os.path.exists(CLOSE_MODEL):
        raise FileNotFoundError(f"Custom model not found: {CLOSE_MODEL}")


driver = None  # Keep browser session available globally


def play_sound(sound: str = "Tink") -> None:
    """Play a macOS system sound. Common options: Tink, Pop, Blow, Ping, Basso."""
    subprocess.Popen(["afplay", f"/System/Library/Sounds/{sound}.aiff"])


def create_driver():
    global driver

    if driver:
        try:
            # Check if browser is still alive
            _ = driver.current_url
            return driver
        except Exception:
            driver = None

    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={SELENIUM_PROFILE}")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def open_sesame() -> None:
    print("\n🌐 Opening Sesame...")

    d = create_driver()
    d.get(TARGET_URL)

    button = WebDriverWait(d, BUTTON_TIMEOUT).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, AGENT_SELECTOR))
    )

    time.sleep(0.5)
    button.click()

    print(f"✅ Clicked {AGENT_NAME}!")


def close_sesame() -> None:
    global driver

    if not driver:
        print("\n⚠️ No active Sesame browser.")
        return

    try:
        print("\n👋 Closing Sesame...")
        driver.quit()  # quit() shuts down the full browser process, not just the tab
        driver = None
        print("✅ Sesame closed.")
    except Exception as e:
        print(f"⚠️ Could not close Sesame: {e}")
        driver = None  # Reset even on failure so next open_sesame() starts fresh


def main() -> None:
    validate_config()

    print("⬇️  Downloading models (first run only)...")
    openwakeword.utils.download_models()

    model = Model(
        wakeword_models=[OPEN_WORD, CLOSE_MODEL],
        vad_threshold=0.5,
    )

    audio = pyaudio.PyAudio()
    stream = audio.open(
        rate=SAMPLE_RATE,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )

    print(f'\n🎙  Listening for "{OPEN_WORD}" (open)')
    print(f'🎙  Listening for "{CLOSE_WORD}" (close)')
    print("Press Ctrl+C to quit.\n")

    try:
        while True:
            raw = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frame = np.frombuffer(raw, dtype=np.int16)

            predictions = model.predict(frame)

            open_score  = predictions.get(OPEN_WORD, 0)
            close_score = predictions.get(CLOSE_WORD, 0)

            if open_score >= THRESHOLD:
                print(f'\n🎯 Detected OPEN word: "{OPEN_WORD}" ({open_score:.2f})')
                play_sound("Ping")
                try:
                    open_sesame()
                except Exception as e:
                    print(f"⚠️ Open error: {e}")
                model.reset()
                time.sleep(2)

            elif close_score >= THRESHOLD:
                print(f'\n🎯 Detected CLOSE word: "{CLOSE_WORD}" ({close_score:.2f})')
                play_sound("Blow")
                close_sesame()
                model.reset()
                time.sleep(2)

    except KeyboardInterrupt:
        print("\n👋 Stopped.")

    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()