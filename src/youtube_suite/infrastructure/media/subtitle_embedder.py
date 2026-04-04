from __future__ import annotations

import subprocess
from pathlib import Path

from youtube_suite.config.settings import get_settings


def embed_subtitles(video_path: Path, srt_path: Path, output_path: Path) -> Path:
    """Burn an SRT subtitle file into a video using ffmpeg's subtitles filter.

    Args:
        video_path: Path to the source video file.
        srt_path: Path to the SRT subtitle file to embed.
        output_path: Destination path for the output video with burned-in subtitles.

    Returns:
        Path to the output video file.

    Raises:
        RuntimeError: If ffmpeg exits with a non-zero return code.
    """
    ffmpeg = get_settings().ffmpeg_path
    filter_arg = f"subtitles='{Path(srt_path).as_posix()}'"
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        filter_arg,
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg failed while embedding subtitles: {exc.stderr.decode(errors='ignore')}"
        ) from exc
    return Path(output_path)
