"""Microphone loop and openWakeWord inference."""

import time
from contextlib import suppress

import numpy as np
import pyaudio
from openwakeword.model import Model

from sesame_wake.config import (
    CHUNK_SIZE,
    COOLDOWN_SECS,
    NEAR_MISS_THRESHOLD,
    SAMPLE_RATE,
    THRESHOLD,
    AppConfig,
)
from sesame_wake.logging_setup import log
from sesame_wake.session import SessionManager


def _load_wake_model(config: AppConfig) -> tuple[Model, str]:
    log.info("Loading wake model from: %s", config.wake_model_path)
    model = Model(wakeword_model_paths=[str(config.wake_model_path)], vad_threshold=0.5)
    return model, next(iter(model.models.keys()))


def run_listener(session: SessionManager, config: AppConfig) -> None:
    model, score_key = _load_wake_model(config)

    audio = pyaudio.PyAudio()
    stream = None

    try:
        stream = _open_audio_stream(audio)
        log.info('🎙  Listening for "%s" (toggle open/close)', score_key)
        log.info("Press Ctrl+C to quit.")

        while True:
            frame = _read_audio_frame(stream)
            if frame is None:
                log.warning("Microphone error — attempting to reopen stream...")
                time.sleep(1)
                stream = _open_audio_stream(audio)
                continue

            score = model.predict(frame).get(score_key, 0)

            if score >= THRESHOLD:
                action = "CLOSE" if session.is_active else "OPEN"
                log.info('🎯 Detected "%s" (%.2f) → %s', score_key, score, action)
                session.toggle()
                model.reset()
                time.sleep(COOLDOWN_SECS)

            elif score >= NEAR_MISS_THRESHOLD:
                log.debug('Near-miss "%s": %.2f', score_key, score)

    except KeyboardInterrupt:
        log.info("👋 Stopped by user.")

    finally:
        if stream:
            with suppress(Exception):
                stream.stop_stream()
                stream.close()
        audio.terminate()


def _open_audio_stream(audio: pyaudio.PyAudio) -> pyaudio.Stream:
    """Open the microphone stream, with a clear error if no device is found."""
    try:
        return audio.open(
            rate=SAMPLE_RATE,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
    except OSError as e:
        log.error("Could not open microphone: %s", e)
        raise


def _read_audio_frame(stream: pyaudio.Stream) -> np.ndarray | None:
    """
    Read one audio frame. Returns None on recoverable mic errors
    so the main loop can attempt to reopen the stream.
    """
    try:
        raw = stream.read(CHUNK_SIZE, exception_on_overflow=False)
        return np.frombuffer(raw, dtype=np.int16)
    except OSError as e:
        log.warning("Audio read error (mic disconnected?): %s", e)
        return None
