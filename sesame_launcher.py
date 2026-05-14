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
Wake word launcher for Sesame (dedicated Chrome profile).

Wake word:
- **Required:** set ``WAKE_MODEL`` in ``.env`` to the ONNX filename under ``models/``
  (see README). Toggles Sesame open/closed.

Configuration:
- Copy .env.example to .env and set ``SELENIUM_PROFILE`` and ``WAKE_MODEL``.

Implementation lives in the `sesame_wake` package; this file stays as a
PEP 723 runnable script and compatibility entry for tooling.
"""

import sys
from pathlib import Path

# PEP 723 runs may not install this repo as a package — ensure repo root is importable.
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sesame_wake.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
