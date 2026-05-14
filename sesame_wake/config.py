"""Constants and environment validation."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR = _REPO_ROOT / "models"
_ASSETS_DIR = _REPO_ROOT / "assets"

load_dotenv()

AGENT_NAME = "Miles"
AGENT_SELECTOR = f'[aria-label="{AGENT_NAME}"]'

TARGET_URL = "https://app.sesame.com/"
THRESHOLD = 0.7
NEAR_MISS_THRESHOLD = 0.5
BUTTON_TIMEOUT = 15
OPEN_RETRIES = 3
RETRY_DELAY = 2.0
COOLDOWN_SECS = 2
CHUNK_SIZE = 1280
SAMPLE_RATE = 16000
LOG_FILE = "sesame_wake.log"

_HINT_URL = "https://github.com/fwartner/home-assistant-wakewords-collection/tree/main"


@dataclass(frozen=True)
class AppConfig:
    selenium_profile: str
    wake_model_path: Path
    start_sound: Path
    end_sound: Path


def load_config() -> AppConfig:
    """Fail fast with clear messages, then return non-optional runtime config."""
    profile = os.getenv("SELENIUM_PROFILE")
    if not profile:
        raise ValueError("SELENIUM_PROFILE is not set in .env")

    model_name = os.getenv("WAKE_MODEL", "").strip()
    if not model_name:
        raise ValueError(f"WAKE_MODEL is required in .env. See {_HINT_URL}")

    # Ensure we only use the filename to stay within the models directory
    model_path = (_MODELS_DIR / Path(model_name).name).resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"Model missing at {model_path}. See {_HINT_URL}")

    start_sound = _ASSETS_DIR / "start_call.mp3"
    end_sound = _ASSETS_DIR / "end_call.mp3"

    for path in (start_sound, end_sound):
        if not path.is_file():
            raise FileNotFoundError(f"Missing asset: {path}")

    return AppConfig(
        selenium_profile=profile,
        wake_model_path=model_path,
        start_sound=start_sound,
        end_sound=end_sound,
    )
