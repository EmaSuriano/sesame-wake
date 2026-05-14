"""Microphone loop and openWakeWord inference."""

import time
from collections import deque
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from threading import Event

import numpy as np
import pyaudio
from openwakeword.model import Model

from sesame_wake.config import (
    CHUNK_SIZE,
    COOLDOWN_SECS,
    NEAR_MISS_THRESHOLD,
    SAMPLE_RATE,
    SPEAKER_THRESHOLD,
    THRESHOLD,
    AppConfig,
)
from sesame_wake.logging_setup import log
from sesame_wake.session import SessionManager
from sesame_wake.speaker import SpeakerVerifier


@dataclass(frozen=True)
class ListenerEvent:
    kind: str
    message: str
    score: float | None = None
    action: str | None = None


ListenerEventHandler = Callable[[ListenerEvent], None]


def _emit(events: ListenerEventHandler | None, event: ListenerEvent) -> None:
    if events:
        events(event)


def _load_wake_model(config: AppConfig) -> tuple[Model, str]:
    log.info("Loading wake model from: %s", config.wake_model_path)
    model = Model(wakeword_model_paths=[str(config.wake_model_path)], vad_threshold=0.5)
    return model, next(iter(model.models.keys()))


def run_listener(
    session: SessionManager,
    config: AppConfig,
    *,
    events: ListenerEventHandler | None = None,
    stop_event: Event | None = None,
) -> None:
    model, score_key = _load_wake_model(config)
    verifier = SpeakerVerifier(config) if config.speaker_verification_enabled else None
    audio_frames = deque[np.ndarray](
        maxlen=max(1, int((SPEAKER_THRESHOLD * SAMPLE_RATE) / CHUNK_SIZE))
    )

    audio = pyaudio.PyAudio()
    stream = None
    level_emit_at = 0.0

    try:
        stream = _open_audio_stream(audio)
        log.info('🎙  Listening for "%s" (toggle open/close)', score_key)
        log.info("Press Ctrl+C to quit.")
        _emit(events, ListenerEvent("ready", f'Listening for "{score_key}"'))

        while stop_event is None or not stop_event.is_set():
            frame = _read_audio_frame(stream)
            if frame is None:
                log.warning("Microphone error — attempting to reopen stream...")
                _emit(events, ListenerEvent("microphone", "Microphone error; reopening stream"))
                time.sleep(1)
                stream = _open_audio_stream(audio)
                continue

            now = time.monotonic()
            if now >= level_emit_at:
                _emit(
                    events,
                    ListenerEvent("input_level", "Microphone level updated", _audio_level(frame)),
                )
                level_emit_at = now + 0.1
            audio_frames.append(frame.copy())
            score = model.predict(frame).get(score_key, 0)
            _emit(events, ListenerEvent("score", "Wake score updated", float(score)))

            if score >= THRESHOLD:
                log.info('🎯 Detected "%s" (%.2f)', score_key, score)
                _emit(
                    events,
                    ListenerEvent("detected", f'Detected "{score_key}"', float(score)),
                )
                if verifier is not None:
                    verified, similarity = verifier.verify(np.concatenate(audio_frames))
                    if not verified:
                        log.warning(
                            "Rejected wake word: speaker similarity %.2f below threshold %.2f",
                            similarity,
                            verifier.threshold,
                        )
                        _emit(
                            events,
                            ListenerEvent(
                                "speaker_rejected",
                                "Wake word rejected: speaker did not match",
                                similarity,
                            ),
                        )
                        model.reset()
                        time.sleep(COOLDOWN_SECS)
                        continue

                    log.info("Speaker verified (similarity %.2f)", similarity)
                    _emit(
                        events,
                        ListenerEvent("speaker_verified", "Speaker verified", similarity),
                    )

                action = session.toggle()
                _emit(
                    events,
                    ListenerEvent(
                        "toggled",
                        f"{action.replace('_', ' ').title()} finished",
                        float(score),
                        action,
                    ),
                )
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


def _audio_level(frame: np.ndarray) -> float:
    """Return an approximate 0..1 RMS level for int16 microphone samples."""
    if frame.size == 0:
        return 0.0
    rms = np.sqrt(np.mean(frame.astype(np.float32) ** 2))
    return min(1.0, float(rms / np.iinfo(np.int16).max))
