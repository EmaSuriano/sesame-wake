# sesame-wake

Voice-activated launcher for [Sesame](https://app.sesame.com/). It listens for a local
openWakeWord-compatible ONNX model, then uses Selenium to open or close Sesame in Chrome.

You must provide your own wake-word model. A large community collection is available in
[home-assistant-wakewords-collection](https://github.com/fwartner/home-assistant-wakewords-collection/tree/main).

https://github.com/user-attachments/assets/925273e5-3d3a-4595-8515-70164d23004a

## What It Does

- Captures microphone audio locally with PyAudio.
- Runs wake-word inference with openWakeWord.
- Optionally verifies the speaker against a local enrolled voice profile before toggling.
- Shows a Textual terminal UI with wake score, mic level, browser state, and recent events.
- Toggles Sesame through Selenium in a dedicated Chrome profile.

Wake-word processing and speaker verification stay on-device; microphone audio is not sent to
a server by this app. The speaker model may be downloaded the first time you enroll or verify.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- Google Chrome
- A working default microphone
- An openWakeWord-compatible `.onnx` model

On macOS, feedback sounds use `afplay`. Linux uses `aplay`; Windows uses PowerShell's
`Media.SoundPlayer`.

## Setup

Clone and install:

```bash
git clone https://github.com/emasuriano/sesame-wake.git
cd sesame-wake
uv sync
```

Create your environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
SELENIUM_PROFILE=/Users/your-username/selenium-sesame-profile
WAKE_MODEL=wakeword.onnx
SPEAKER_VERIFICATION=false
```

Download or train an openWakeWord-compatible ONNX model, then place it under `models/`:

```text
models/wakeword.onnx
```

`WAKE_MODEL` is interpreted as a filename inside `models/`; parent paths are ignored.

## Chrome Profile

Use a dedicated Chrome profile so Selenium does not conflict with your normal browser session.

macOS example:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --user-data-dir=/Users/your-username/selenium-sesame-profile
```

In that browser window, log in to [app.sesame.com](https://app.sesame.com), then close Chrome.
The launcher reuses that profile on future runs.

## Usage

Run the Textual UI:

```bash
uv run sesame-wake
```

Controls:

| Key | Action |
|---|---|
| `t` | Toggle Sesame manually |
| `e` | Enroll speaker profile |
| `q` | Quit |

The UI shows:

- Browser state: open or closed
- Wake score and configured threshold
- Microphone input level
- Recent listener, Selenium, and error events

For plain log output:

```bash
uv run sesame-wake --plain
```

You can also run the package module directly:

```bash
uv run python -m sesame_wake.cli
```

The compatibility shim still works:

```bash
uv run sesame_launcher.py
```

## Speaker Verification

Speaker verification adds a local voice match before the app opens or closes Sesame. It is meant
to reduce accidental or casual use by other people nearby; it is not secure authentication and may
be fooled by a recording of your voice.

First enroll your voice:

```bash
uv run sesame-wake --enroll-speaker
```

You can also press `e` in the Textual UI. The app pauses wake listening, records the speaker
profile, saves it, and then resumes listening.

Speak naturally for the enrollment window. You can override the duration in seconds:

```bash
uv run sesame-wake --enroll-speaker 30
```

Then enable verification in `.env`:

```env
SPEAKER_VERIFICATION=true
SPEAKER_PROFILE=profiles/speaker.npy
SPEAKER_THRESHOLD=0.55
SPEAKER_WINDOW_SECS=3.0
SPEAKER_ENROLL_SECS=20.0
```

Higher `SPEAKER_THRESHOLD` values reject more non-matching voices but may also reject you in noisy
conditions. Lower values are more forgiving but less protective.

## Configuration

Required `.env` settings:

| Setting | Description |
|---|---|
| `SELENIUM_PROFILE` | Chrome `--user-data-dir` path used by Selenium |
| `WAKE_MODEL` | ONNX filename inside `models/` |
| `SPEAKER_VERIFICATION` | Optional `true`/`false` speaker check before toggling |
| `SPEAKER_PROFILE` | Local `.npy` voice profile created by `--enroll-speaker` |
| `SPEAKER_THRESHOLD` | Cosine similarity required to accept the speaker |
| `SPEAKER_WINDOW_SECS` | Recent microphone audio used for verification after wake detection |
| `SPEAKER_ENROLL_SECS` | Default enrollment recording duration |

Runtime constants live in `sesame_wake/config.py`.

Current wake tuning:

| Constant | Value | Purpose |
|---|---:|---|
| `THRESHOLD` | `0.7` | Wake score required to toggle Sesame |
| `NEAR_MISS_THRESHOLD` | `0.5` | Debug logging threshold for near misses |

Lower `THRESHOLD` values increase sensitivity and false positives. Higher values reduce false
positives but may miss quieter speech.

## Wake Models

This project does not bundle wake models and does not call openWakeWord's bulk
`download_models()` helper.

Options:

- Download a community ONNX model from
  [home-assistant-wakewords-collection](https://github.com/fwartner/home-assistant-wakewords-collection/tree/main).
- Train your own model with the
  [openWakeWord Colab notebook](https://colab.research.google.com/drive/1q1oe2zOyZp7UsB3jJiQ1IFn8z5YfjwEb).

Save the file as `models/<name>.onnx`, then set `WAKE_MODEL=<name>.onnx` in `.env`.

## Development

Run the same checks as CI:

```bash
uv run --locked --only-group dev ruff check .
uv run --locked --only-group dev ruff format --check .
uv run --locked --only-group dev python -m compileall sesame_wake sesame_launcher.py
uv build --sdist --wheel
```

GitHub Actions runs these checks on pull requests and pushes to `main`.

## Project Structure

```text
sesame-wake/
├── .github/workflows/ci.yml
├── assets/                  # Feedback sounds
├── models/                  # Put your ONNX wake model here
├── sesame_wake/
│   ├── cli.py               # Console entry point
│   ├── config.py            # Env loading, constants, AppConfig
│   ├── listener.py          # PyAudio + openWakeWord loop
│   ├── logging_setup.py
│   ├── session.py           # Selenium browser lifecycle
│   ├── sounds.py
│   └── tui.py               # Textual UI
├── sesame_launcher.py       # Backward-compatible launcher shim
├── pyproject.toml
├── uv.lock
└── README.md
```

## Troubleshooting

**Wake word fires too often**

- Increase `THRESHOLD` in `sesame_wake/config.py`.
- Watch the wake score in the UI while speaking normally and while saying the wake phrase.

**Wake word is not detected**

- Lower `THRESHOLD` in `sesame_wake/config.py`.
- Confirm your default microphone is the one you are speaking into.
- Confirm `WAKE_MODEL` points to an existing file under `models/`.
- Watch the mic level meter; if it does not move, the app is not receiving microphone input.

**Chrome fails to open**

- Confirm Chrome is installed.
- Confirm `SELENIUM_PROFILE` points to a writable profile directory.
- Launch Chrome manually once with that profile and log in to Sesame.

**Sesame button is not found**

- Sesame may have changed its UI.
- Inspect the agent button in Chrome DevTools.
- Update `AGENT_NAME` or `AGENT_SELECTOR` in `sesame_wake/config.py`.

**openWakeWord reports missing preprocessor files**

- Prefer `uv sync` and `uv run sesame-wake` so your installed versions match `uv.lock`.
- If you installed manually, align your dependency versions with `pyproject.toml` and `uv.lock`.

## Acknowledgements

- [openWakeWord](https://github.com/dscripka/openWakeWord)
- [Textual](https://github.com/Textualize/textual)
- [home-assistant-wakewords-collection](https://github.com/fwartner/home-assistant-wakewords-collection)
- [Sesame](https://app.sesame.com/)

## License

MIT
