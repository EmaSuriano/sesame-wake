# sesame-wake

Voice-activated launcher for [Sesame](https://app.sesame.com/): local wake-word detection with [openWakeWord](https://github.com/dscripka/openWakeWord), then Selenium drives Chrome to open or close the app. **You must supply your own** openWakeWord-compatible `.onnx` wake model (see `.env`); a large community collection is maintained in [home-assistant-wakewords-collection](https://github.com/fwartner/home-assistant-wakewords-collection/tree/main).

https://github.com/user-attachments/assets/925273e5-3d3a-4595-8515-70164d23004a

---

## How It Works

Audio is captured from your microphone in real time, fed into the wake model, and when the score is above the threshold, Selenium toggles Sesame in a dedicated Chrome profile.

All wake-word processing is **on-device** — no audio is sent to any server.

```
Microphone → openWakeWord → threshold check → Selenium → Sesame
```

---

## Requirements

- **Python 3.11+**
- **Google Chrome** (Selenium uses your Chrome install)
- A working **microphone** as the default input device
- On macOS, **`afplay`** is used for optional MP3 feedback sounds; Linux/Windows use `aplay` / PowerShell with varying format support (MP3 is most reliable on macOS)

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/emasuriano/sesame-wake.git
cd sesame-wake
```

*(If the GitHub repository is still under another name, use that URL instead.)*

### 2. Install dependencies

This project uses [uv](https://github.com/astral-sh/uv):

```bash
uv sync
```

Or install manually with pip:

```bash
pip install openwakeword pyaudio numpy selenium python-dotenv
```

### 3. Configure your environment

```bash
cp .env.example .env
```

Edit `.env` and set **`SELENIUM_PROFILE`**, **`WAKE_MODEL`** (the ONNX filename inside `models/`), and create a Chrome profile as below.

```env
SELENIUM_PROFILE=/Users/your-username/selenium-sesame-profile
WAKE_MODEL=wakeword.onnx
```

That loads `models/wakeword.onnx` (you can also set `WAKE_MODEL=wakeword.onnx`).

**Wake models:** This project does **not** bundle or load openWakeWord’s built-in wake checkpoints. Download an `.onnx` from the community [home-assistant-wakewords-collection](https://github.com/fwartner/home-assistant-wakewords-collection/tree/main) (or train your own with the [openWakeWord Colab](https://colab.research.google.com/drive/1q1oe2zOyZp7UsB3jJiQ1IFn8z5YfjwEb)), save it as `models/<name>.onnx`, and set **`WAKE_MODEL`** to `<name>` (or the full filename).

> **Tip:** Using a dedicated Chrome profile (separate from your main one) avoids conflicts and keeps Sesame's session persistent between runs.

### 4. Create a dedicated Chrome profile

**macOS example** — run Chrome once with the profile path, log in to Sesame, then close the window:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --user-data-dir=/Users/your-username/selenium-sesame-profile
```

On Linux or Windows, start Chrome with the same `--user-data-dir` idea using your install path.

Log in to [app.sesame.com](https://app.sesame.com) inside that window, then close it. The launcher reuses this session on the next run.

> Logging into Sesame allows longer sessions than guest use.

---

## Usage

From the repo root, install the project (uses `uv.lock`) then run the console script:

```bash
uv sync
sesame-wake
```

Or run the PEP 723 entry script (resolves its own dependencies from the script header, which may differ from `uv.lock`):

```bash
uv run sesame_launcher.py
```

Or the package module:

```bash
uv run python -m sesame_wake.cli
```

Sample log output:

```
🎙  Listening for "wakeword" (toggle open/close)
Press Ctrl+C to quit.
```

The quoted wake string is the **model key** openWakeWord uses (often the `.onnx` filename stem).

Only your **`models/<WAKE_MODEL>.onnx`** wake network is loaded. This launcher does **not** call openWakeWord’s bulk `download_models()` helper (that can pull many assets); use **`uv sync`** with this repo’s `uv.lock` so the wheel includes the shared preprocessor weights your install expects.

| Trigger | Action |
|---|---|
| **Wake score above threshold** | Opens Sesame (if closed) or closes the browser session (if open) |

Press `Ctrl+C` to stop.

---

## Wake models (bring your own ONNX)

1. Obtain an openWakeWord-compatible `.onnx` file, for example from the community [home-assistant-wakewords-collection](https://github.com/fwartner/home-assistant-wakewords-collection/tree/main).
2. Copy it into this repo’s `models/` directory as e.g. `models/wakeword.onnx`.
3. Set **`WAKE_MODEL=wakeword`** in `.env` (stem or full `wakeword.onnx` name).

To train a brand-new phrase from scratch, use the [openWakeWord Colab notebook](https://colab.research.google.com/drive/1q1oe2zOyZp7UsB3jJiQ1IFn8z5YfjwEb) or the [openWakeWord](https://github.com/dscripka/openWakeWord) docs. Phonetic spellings with underscores often work better for synthetic training data.

---

## Configuration

| Setting | Where | Description |
|---|---|---|
| `SELENIUM_PROFILE` | `.env` | Chrome `--user-data-dir` (required) |
| `WAKE_MODEL` | `.env` | **Required.** ONNX filename for `models/<name>.onnx` (stem or `name.onnx`). |
| Thresholds, timeouts, agent name, … | `sesame_wake/config.py` | Edit constants or extend with env reads as needed. |

**Tuning the threshold:** Lower values (`0.3`) increase sensitivity and false positives. Higher values (`0.7`) reduce false positives but may miss quieter speech.

---

## Project Structure

```
sesame-wake/
├── sesame_wake/
│   ├── config.py        # Env + constants, load_config
│   ├── logging_setup.py
│   ├── sounds.py
│   ├── session.py       # Selenium SessionManager
│   ├── listener.py      # Wake loop (PyAudio + openWakeWord)
│   └── cli.py           # main()
├── sesame_launcher.py   # PEP 723 entry + `uv run` shim
├── models/              # Put your .onnx wake model here (see .env.example)
├── assets/              # Optional feedback MP3s
├── .env
├── .env.example
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Troubleshooting

**openWakeWord missing preprocessor files (melspectrogram / embedding)**

- Prefer **`uv sync`** + **`sesame-wake`** so versions match `uv.lock`. If you use **`uv run sesame_launcher.py`**, the PEP 723 block may resolve a different openWakeWord build; align it with `pyproject.toml` or run a one-off download from upstream docs if your build expects extra files on disk.

**Wake word not being detected**

- Lower `THRESHOLD` in `sesame_wake/config.py` and test again.
- Use a default input device that matches the mic you are speaking into.
- For custom models, confirm `WAKE_MODEL` and `models/<name>.onnx` exist; inspect `model.predict(frame)` keys if scores stay at zero.

**Chrome fails to open**

- Ensure Chrome is installed and Selenium can launch it (driver requirements depend on your Selenium/Chrome version).
- Confirm `SELENIUM_PROFILE` in `.env` points at an existing directory.

**Wrong prediction key in logs**

- The string logged is the internal **model key** (often the ONNX stem). Use that key when debugging `predict` output.

**Sesame button not found**

- The `aria-label` selector may have changed. Inspect the button in Chrome DevTools and update `AGENT_SELECTOR` / `AGENT_NAME` in `sesame_wake/config.py`.

---

## Acknowledgements

- [openWakeWord](https://github.com/dscripka/openWakeWord) by David Scripka.
- [home-assistant-wakewords-collection](https://github.com/fwartner/home-assistant-wakewords-collection) — community wake ONNX models.
- [Sesame](https://app.sesame.com/).

---

## License

MIT
