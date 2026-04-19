"""Audio extraction and analysis utilities."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_path: str, sample_rate: int = 16000, channels: int = 1) -> str:
    """Extract audio from a video file using FFmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ac", str(channels),
        "-ar", str(sample_rate),
        "-vn",
        output_path,
    ]
    logger.info("Extracting audio from %s → %s", video_path, output_path)
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    if not Path(output_path).exists():
        raise FileNotFoundError(f"Audio not created: {output_path}")
    logger.info("Audio extracted: %s", output_path)
    return output_path


def get_audio_duration(audio_path: str) -> float:
    """Return duration of an audio file in seconds using FFprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning("Could not get audio duration: %s", e)
        return 0.0


def analyze_audio_features(audio_path: str, start: float, end: float) -> dict[str, float]:
    """Extract real audio features for a time segment using librosa.

    Returns a dict with normalised (0-1) values for:
        rms_energy, zcr_mean, spectral_centroid, silence_ratio

    Falls back to neutral 0.5 values if librosa is unavailable.
    """
    try:
        import librosa  # optional dep — in [shorts]
    except ImportError:
        logger.debug("librosa not installed — returning neutral audio features")
        return {"rms_energy": 0.5, "zcr_mean": 0.5, "spectral_centroid": 0.5, "silence_ratio": 0.3}

    try:
        duration = max(end - start, 0.1)
        y, sr = librosa.load(audio_path, sr=None, offset=start, duration=duration, mono=True)

        if len(y) == 0:
            return {"rms_energy": 0.0, "zcr_mean": 0.0, "spectral_centroid": 0.0, "silence_ratio": 1.0}

        rms_frames = librosa.feature.rms(y=y)[0]
        rms_energy = float(np.clip(np.mean(rms_frames) * 12, 0, 1))

        zcr_frames = librosa.feature.zero_crossing_rate(y)[0]
        zcr_mean = float(np.clip(np.mean(zcr_frames) * 8, 0, 1))

        centroid_frames = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_centroid = float(np.clip(np.mean(centroid_frames) / (sr / 2), 0, 1))

        silence_threshold = 0.008
        silence_ratio = float(np.mean(rms_frames < silence_threshold))

        return {
            "rms_energy": rms_energy,
            "zcr_mean": zcr_mean,
            "spectral_centroid": spectral_centroid,
            "silence_ratio": silence_ratio,
        }
    except Exception as e:
        logger.warning("Error analysing audio features [%.1f-%.1f]: %s", start, end, e)
        return {"rms_energy": 0.5, "zcr_mean": 0.5, "spectral_centroid": 0.5, "silence_ratio": 0.3}
