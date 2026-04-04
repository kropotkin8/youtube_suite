from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from youtube_suite.config.settings import get_settings


@dataclass
class AudioChunk:
    index: int
    path: Path
    start_offset: float   # actual extraction start in the video (includes overlap pullback)
    logical_start: float  # boundary where this chunk's unique content begins (no overlap)
    duration: float       # requested duration (seconds); last chunk may be shorter


def _get_video_duration(video_path: Path) -> float:
    """Use ffprobe to get the total duration of a video/audio file in seconds."""
    s = get_settings()
    ffprobe = Path(s.ffmpeg_path).parent / "ffprobe"
    cmd = [
        str(ffprobe),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def split_audio_into_chunks(
    video_path: Path,
    output_dir: Path,
    chunk_seconds: int,
    overlap_seconds: int,
    job_id: uuid.UUID,
) -> list[AudioChunk]:
    """Extract overlapping WAV chunks from *video_path* using ffmpeg.

    Each chunk is extracted directly from the source video (no full WAV
    materialisation), keeping peak memory bounded to a single chunk's size.

    Args:
        video_path: Source video file.
        output_dir: Directory where chunk WAV files are written.
        chunk_seconds: Logical chunk length in seconds (without overlap).
        overlap_seconds: Extra seconds included at the start of each chunk
            (except chunk 0) so boundary words are not cut.
        job_id: Used to namespace chunk files under ``output_dir/{job_id}/``.

    Returns:
        List of :class:`AudioChunk` in chronological order.
    """
    s = get_settings()
    total_duration = _get_video_duration(video_path)

    chunk_dir = output_dir / str(job_id)
    chunk_dir.mkdir(parents=True, exist_ok=True)

    chunks: list[AudioChunk] = []
    logical_start = 0.0
    index = 0

    while logical_start < total_duration:
        actual_start = max(0.0, logical_start - (overlap_seconds if index > 0 else 0))
        remaining = total_duration - actual_start
        duration = min(chunk_seconds + (overlap_seconds if index > 0 else 0), remaining)

        chunk_path = chunk_dir / f"chunk_{index:04d}.wav"
        cmd = [
            str(s.ffmpeg_path),
            "-y",
            "-ss", str(actual_start),
            "-i", str(video_path),
            "-t", str(duration),
            "-ac", "1",
            "-ar", "16000",
            str(chunk_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        chunks.append(AudioChunk(
            index=index,
            path=chunk_path,
            start_offset=actual_start,
            logical_start=logical_start,
            duration=duration,
        ))

        logical_start += chunk_seconds
        index += 1

    return chunks
