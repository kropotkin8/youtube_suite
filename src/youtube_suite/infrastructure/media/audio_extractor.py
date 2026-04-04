from __future__ import annotations

import subprocess
from pathlib import Path

from youtube_suite.config.settings import get_settings


def extract_audio(
    video_path: Path,
    output_path: Path | None = None,
    sample_rate: int = 16000,
) -> Path:
    """Extract a mono WAV audio track from a video file using ffmpeg.

    Args:
        video_path: Path to the source video file.
        output_path: Destination WAV path. Defaults to the video path with a ``.wav`` extension.
        sample_rate: Output audio sample rate in Hz.

    Returns:
        Path to the extracted WAV file.

    Raises:
        RuntimeError: If ffmpeg exits with a non-zero return code.
    """
    video_path = Path(video_path)
    if output_path is None:
        output_path = video_path.with_suffix(".wav")
    output_path = Path(output_path)
    ffmpeg = get_settings().ffmpeg_path
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg failed while extracting audio: {exc.stderr.decode(errors='ignore')}"
        ) from exc
    return output_path
