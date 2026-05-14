"""Local speaker enrollment and verification."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pyaudio

from sesame_wake.config import (
    CHUNK_SIZE,
    SAMPLE_RATE,
    SPEAKER_ENROLL_SECS,
    SPEAKER_MODEL_CACHE,
    SPEAKER_MODEL_SOURCE,
    SPEAKER_THRESHOLD,
    AppConfig,
)
from sesame_wake.logging_setup import log

if TYPE_CHECKING:
    from speechbrain.inference.speaker import EncoderClassifier


EnrollmentProgressHandler = Callable[[float, float], None]


def _load_classifier() -> EncoderClassifier:
    try:
        from speechbrain.inference.speaker import EncoderClassifier
    except ImportError as e:
        raise RuntimeError(
            "Speaker verification requires SpeechBrain. Run `uv sync` after updating dependencies."
        ) from e

    return EncoderClassifier.from_hparams(
        source=SPEAKER_MODEL_SOURCE,
        savedir=str(SPEAKER_MODEL_CACHE),
    )


class SpeakerVerifier:
    """Compare recent microphone audio against an enrolled local voiceprint."""

    def __init__(self, config: AppConfig) -> None:
        self.threshold = SPEAKER_THRESHOLD
        self.profile_path = config.speaker_profile_path
        self.classifier = _load_classifier()
        self.reference_embedding = _load_embedding(self.profile_path)

    def verify(self, samples: np.ndarray) -> tuple[bool, float]:
        embedding = self._embedding(samples)
        similarity = _cosine_similarity(self.reference_embedding, embedding)
        return similarity >= self.threshold, similarity

    def _embedding(self, samples: np.ndarray) -> np.ndarray:
        import torch

        waveform = _int16_to_float32(samples)
        if waveform.size == 0:
            return np.array([], dtype=np.float32)
        with torch.no_grad():
            tensor = torch.from_numpy(waveform).unsqueeze(0)
            embedding = self.classifier.encode_batch(tensor).squeeze().cpu().numpy()
        return np.asarray(embedding, dtype=np.float32)


def enroll_speaker(
    config: AppConfig,
    seconds: float | None = None,
    *,
    progress: EnrollmentProgressHandler | None = None,
) -> Path:
    """Record microphone audio and save a speaker embedding for later verification."""
    duration = seconds or SPEAKER_ENROLL_SECS
    if duration <= 0:
        raise ValueError("Enrollment duration must be greater than zero")

    log.info("Loading speaker model from %s", SPEAKER_MODEL_SOURCE)
    classifier = _load_classifier()
    log.info("Recording %.1f seconds for speaker enrollment...", duration)
    samples = _record_microphone(duration, progress=progress)
    embedding = _extract_embedding(classifier, samples)

    config.speaker_profile_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(config.speaker_profile_path, embedding)
    log.info("Saved speaker profile: %s", config.speaker_profile_path)
    return config.speaker_profile_path


def _record_microphone(
    seconds: float,
    *,
    progress: EnrollmentProgressHandler | None = None,
) -> np.ndarray:
    audio = pyaudio.PyAudio()
    stream = None
    frames: list[np.ndarray] = []
    total_frames = max(1, int((seconds * SAMPLE_RATE) / CHUNK_SIZE))

    try:
        stream = audio.open(
            rate=SAMPLE_RATE,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        started = time.monotonic()
        next_progress_at = 0.0
        for index in range(total_frames):
            raw = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frame = np.frombuffer(raw, dtype=np.int16).copy()
            frames.append(frame)
            if progress is not None:
                now = time.monotonic()
                if now >= next_progress_at or index == total_frames - 1:
                    progress((index + 1) / total_frames, _audio_level(frame))
                    next_progress_at = now + 0.1
        elapsed = time.monotonic() - started
        log.info("Captured %.1f seconds of enrollment audio.", elapsed)
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()

    return np.concatenate(frames) if frames else np.array([], dtype=np.int16)


def _extract_embedding(classifier: EncoderClassifier, samples: np.ndarray) -> np.ndarray:
    import torch

    waveform = _int16_to_float32(samples)
    if waveform.size == 0:
        raise ValueError("No enrollment audio was captured")
    with torch.no_grad():
        tensor = torch.from_numpy(waveform).unsqueeze(0)
        embedding = classifier.encode_batch(tensor).squeeze().cpu().numpy()
    return np.asarray(embedding, dtype=np.float32)


def _load_embedding(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(
            f"Speaker profile missing at {path}. Run `uv run sesame-wake --enroll-speaker` first."
        )
    return np.load(path).astype(np.float32)


def _int16_to_float32(samples: np.ndarray) -> np.ndarray:
    return samples.astype(np.float32) / float(np.iinfo(np.int16).max)


def _audio_level(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    rms = np.sqrt(np.mean(frame.astype(np.float32) ** 2))
    return min(1.0, float(rms / np.iinfo(np.int16).max))


def _cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    denominator = np.linalg.norm(left) * np.linalg.norm(right)
    if denominator == 0:
        return 0.0
    return float(np.dot(left, right) / denominator)
