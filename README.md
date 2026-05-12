# 🎙️ hey-jarvis

A macOS voice-activated launcher for [Sesame](https://app.sesame.com/) using local wake word detection. Say **"Hey Jarvis"** to open Sesame and start talking to Miles — say **"Goodbye Jarvis"** to close it. No keyboard, no clicks.

https://github.com/user-attachments/assets/placeholder-demo.mp4

---

## How It Works

The script runs a local wake word detection loop using [openWakeWord](https://github.com/dscripka/openWakeWord). Audio is captured from your microphone in real time, fed into the model, and when a wake word is detected above the confidence threshold, Selenium automates Chrome to open or close Sesame.

All processing is **on-device** — no audio is sent to any server.

```
Microphone → openWakeWord → threshold check → Selenium → Sesame
```

---

## Requirements

- macOS (uses `afplay` for audio feedback)
- Python 3.11+
- Google Chrome
- [ChromeDriver](https://googlechromelabs.github.io/chrome-for-testing/) matching your Chrome version

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/emasuriano/hey-jarvis
cd hey-jarvis
```

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

Edit `.env` and set your Chrome profile path:

```env
SELENIUM_PROFILE=/Users/your-username/selenium-sesame-profile
```

> **Tip:** Using a dedicated Chrome profile (separate from your main one) avoids conflicts and keeps Sesame's session persistent between runs.

### 4. Create a dedicated Chrome profile

Run Chrome once with the profile path to initialize it, then log in to Sesame manually so the session is saved:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --user-data-dir=/Users/your-username/selenium-sesame-profile
```

Log in to [app.sesame.com](https://app.sesame.com) inside that window, then close it. The script will reuse this session from now on.

> ⚠️ Logging into Sesame allows you to have sessions of 30 minutes, instead of 5 minutes for guest users.

### 5. Add the custom wake word model

The `goodbye_jarvis.onnx` model is included in the repo under `models/` — no training needed. If you'd like to retrain it or create your own variant, see [Training a Custom Wake Word](#training-a-custom-wake-word).

---

## Usage

```bash
hey-jarvis
```

Or via uv without installing:

```bash
uv run sesame_launcher.py
```

```
⬇️  Downloading models (first run only)...
🎙  Listening for "hey_jarvis" (open)
🎙  Listening for "goodbye_jarvis" (close)
Press Ctrl+C to quit.
```

| Voice command | Action |
|---|---|
| **"Hey Jarvis"** | Opens Sesame in Chrome and clicks the Miles button |
| **"Goodbye Jarvis"** | Closes the browser session |

Press `Ctrl+C` to stop the script.

---

## Training a Custom Wake Word

The `goodbye_jarvis.onnx` model is already included — you don't need to train anything to get started. This section is for cases where you want to retrain it (e.g. improve accuracy for your voice) or swap in a different wake word entirely.

### Option A: Google Colab (free, recommended)

1. Open the official notebook:
   [colab.research.google.com/drive/1q1oe2zOyZp7UsB3jJiQ1IFn8z5YfjwEb](https://colab.research.google.com/drive/1q1oe2zOyZp7UsB3jJiQ1IFn8z5YfjwEb)

2. Set your target phrase to:
   ```
   good_bye_jar_vis
   ```
   > Underscores help the TTS pronounce each syllable clearly and consistently across synthetic voices. If the result sounds off, try `gud_by_jar_vis` or `good_bye_jhar_vis`.

3. Run all cells. Training takes 30–60 minutes depending on Colab availability.

4. Download the exported `.onnx` file and place it at `models/goodbye_jarvis.onnx`.

### Option B: Outspoken (paid, ~€1)

[outspoken.cloud](https://outspoken.cloud) — enter your phrase, wait ~45 minutes, download the `.onnx`. The first model is free. Good option if Colab is slow or unavailable.

### Option C: Local training with Docker

For full control and reproducibility, use [openwakeword-training](https://github.com/CoreWorxLab/openwakeword-training). Requires Docker and a CUDA-capable GPU. Training takes 4–8 hours.

---

## Configuration

All tuneable values are at the top of `sesame_launcher.py`:

| Variable | Default | Description |
|---|---|---|
| `OPEN_WORD` | `"hey_jarvis"` | Built-in openWakeWord model name |
| `CLOSE_WORD` | `"goodbye_jarvis"` | Key name for the custom model |
| `CLOSE_MODEL` | `"./models/goodbye_jarvis.onnx"` | Path to the custom `.onnx` file |
| `AGENT_NAME` | `"Miles"` | Sesame agent to click (`Miles` or `Maya`) |
| `THRESHOLD` | `0.5` | Detection confidence threshold (0.0–1.0) |
| `BUTTON_TIMEOUT` | `15` | Seconds to wait for the button to appear |
| `CHUNK_SIZE` | `1280` | Audio frames per model prediction (~80ms) |

**Tuning the threshold:** Lower values (`0.3`) make detection more sensitive but increase false positives. Higher values (`0.7`) reduce false positives but may miss quieter speech.

---

## Project Structure

```
hey-jarvis/
├── sesame_launcher.py   # Main script
├── models/
│   └── goodbye_jarvis.onnx  # Pretrained custom model (included)
├── .env                 # Local config (not committed)
├── .env.example         # Template for .env
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Troubleshooting

**Wake word not being detected**
- Lower `THRESHOLD` to `0.3` and test again.
- Make sure your microphone is set as the system default input.
- Try retraining with phonetic spelling (e.g. `good_bye_jar_vis`).

**Chrome fails to open**
- Verify ChromeDriver is installed and matches your Chrome version: `chromedriver --version` vs `Google Chrome --version`.
- Make sure `SELENIUM_PROFILE` in `.env` points to an existing directory.

**`goodbye_jarvis` key not found in predictions**
- Add `print(predictions)` after `model.predict(frame)` to inspect the actual key names.
- The key is derived from the filename stem — rename your `.onnx` file if needed so the stem matches `CLOSE_WORD`.

**Sesame button not found**
- The `aria-label` selector may have changed. Inspect the button in Chrome DevTools and update `AGENT_SELECTOR` in the script.

---

## Acknowledgements

- [openWakeWord](https://github.com/dscripka/openWakeWord) by David Scripka — the on-device wake word engine that powers this project.
- [Sesame](https://app.sesame.com/) — the voice AI this launcher is built for.

---

## License

MIT