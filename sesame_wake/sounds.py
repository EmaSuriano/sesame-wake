"""Cross-platform sound playback."""

import platform
import subprocess
from os import PathLike, fspath

from sesame_wake.logging_setup import log


def play_sound_async(path: str | PathLike[str]) -> None:
    """Play an audio file without blocking."""
    sound_path = fspath(path)
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["afplay", sound_path])
        elif system == "Linux":
            subprocess.Popen(["aplay", sound_path])
        elif system == "Windows":
            subprocess.Popen(
                ["powershell", "-c", f'(New-Object Media.SoundPlayer "{sound_path}").PlaySync()']
            )
        else:
            log.warning("Sound playback not supported on %s", system)
    except FileNotFoundError as e:
        log.warning("Sound player not found: %s", e)
