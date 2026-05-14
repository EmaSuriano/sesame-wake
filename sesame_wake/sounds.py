"""Cross-platform sound playback."""

import platform
import subprocess

from sesame_wake.logging_setup import log


def play_sound_async(path: str) -> None:
    """Play an audio file without blocking."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["afplay", path])
        elif system == "Linux":
            subprocess.Popen(["aplay", path])
        elif system == "Windows":
            subprocess.Popen(
                ["powershell", "-c", f'(New-Object Media.SoundPlayer "{path}").PlaySync()']
            )
        else:
            log.warning("Sound playback not supported on %s", system)
    except FileNotFoundError as e:
        log.warning("Sound player not found: %s", e)
