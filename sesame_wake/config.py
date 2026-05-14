"""Constants and environment validation."""

import os
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR = _REPO_ROOT / "models"

load_dotenv()

START_SOUND = str(_REPO_ROOT / "assets" / "start_call.mp3")
END_SOUND = str(_REPO_ROOT / "assets" / "end_call.mp3")

AGENT_NAME = "Miles"
AGENT_SELECTOR = f'[aria-label="{AGENT_NAME}"]'

TARGET_URL = "https://app.sesame.com/"
THRESHOLD = 0.5
NEAR_MISS_THRESHOLD = 0.3  # log scores above this even if below THRESHOLD
BUTTON_TIMEOUT = 15
OPEN_RETRIES = 3  # how many times to retry open_sesame on failure
RETRY_DELAY = 2.0  # seconds between retries
COOLDOWN_SECS = 2
CHUNK_SIZE = 1280
SAMPLE_RATE = 16000
LOG_FILE = "sesame_wake.log"

SELENIUM_PROFILE = os.getenv("SELENIUM_PROFILE")

_WAKEWORD_DOWNLOAD_HINT = (
    "https://github.com/fwartner/home-assistant-wakewords-collection/tree/main"
)


def wake_model_path() -> str | None:
    """
    Absolute path to ``models/<WAKE_MODEL>`` when ``WAKE_MODEL`` is set and the file exists.

    ``WAKE_MODEL`` must be the full filename including extension (e.g. ``wakeword.onnx``);
    parent paths are ignored so the ONNX always lives under the repo ``models/`` directory.
    """
    raw = os.getenv("WAKE_MODEL", "").strip()
    if not raw:
        return None
    name = Path(raw).name
    if not name or name in (".", ".."):
        return None
    path = (_MODELS_DIR / name).resolve()
    try:
        path.relative_to(_MODELS_DIR.resolve())
    except ValueError:
        return None
    return str(path) if path.is_file() else None


def validate_config() -> None:
    """Fail fast with clear messages if the environment is misconfigured."""
    if not SELENIUM_PROFILE:
        raise ValueError("SELENIUM_PROFILE is not set in .env")
    raw = os.getenv("WAKE_MODEL", "").strip()
    if not raw:
        raise ValueError(
            "WAKE_MODEL must be set in .env to the ONNX filename inside models/ "
            f"(e.g. WAKE_MODEL=wakeword.onnx). Community models: {_WAKEWORD_DOWNLOAD_HINT}"
        )
    if wake_model_path() is None:
        raise FileNotFoundError(
            f"Expected wake model at models/{Path(raw).name} (from WAKE_MODEL={raw!r}). "
            f"File missing. See {_WAKEWORD_DOWNLOAD_HINT}"
        )
    for path in (START_SOUND, END_SOUND):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Missing file: {path}")
