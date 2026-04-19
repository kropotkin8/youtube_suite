"""Video clip extraction utilities — horizontal and 9:16 vertical formats."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def extract_clip(
    input_video: str,
    start_time: float,
    duration: float,
    output_path: str,
    fade_in: float = 0.5,
    fade_out: float = 0.5,
) -> str:
    """Extract a clip segment from a video using FFmpeg."""
    if fade_in > 0 or fade_out > 0:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", input_video,
            "-t", str(duration),
            "-vf", f"fade=t=in:st=0:d={fade_in},fade=t=out:st={duration - fade_out}:d={fade_out}",
            "-af", f"afade=t=in:st=0:d={fade_in},afade=t=out:st={duration - fade_out}:d={fade_out}",
            "-c:v", "libx264", "-c:a", "aac", "-preset", "fast",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", input_video,
            "-t", str(duration),
            "-c", "copy",
            output_path,
        ]

    logger.info("Extracting clip %.1fs–%.1fs → %s", start_time, start_time + duration, output_path)
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    if not Path(output_path).exists():
        raise FileNotFoundError(f"Clip not created: {output_path}")
    return output_path


def extract_vertical_clip(
    input_video: str,
    start_time: float,
    duration: float,
    output_path: str,
    fade_in: float = 0.3,
    fade_out: float = 0.3,
) -> str:
    """Extract a 9:16 vertical crop of a clip for Shorts / Reels / TikTok.

    Crops the horizontal input to 9:16 (centre crop) and scales to 1080×1920.
    """
    fade_filters = ""
    if fade_in > 0 or fade_out > 0:
        fade_filters = (
            f",fade=t=in:st=0:d={fade_in}"
            f",fade=t=out:st={duration - fade_out}:d={fade_out}"
        )
        audio_fade = (
            f"afade=t=in:st=0:d={fade_in},"
            f"afade=t=out:st={duration - fade_out}:d={fade_out}"
        )
    else:
        audio_fade = "anull"

    # crop=ih*9/16:ih:(iw-ih*9/16)/2:0  → centre-crop to 9:16 aspect ratio
    # then scale to 1080×1920
    vf = f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920{fade_filters}"

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", input_video,
        "-t", str(duration),
        "-vf", vf,
        "-af", audio_fade,
        "-c:v", "libx264", "-c:a", "aac", "-preset", "fast",
        output_path,
    ]

    logger.info("Extracting vertical clip %.1fs–%.1fs → %s", start_time, start_time + duration, output_path)
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    if not Path(output_path).exists():
        raise FileNotFoundError(f"Vertical clip not created: {output_path}")
    return output_path


def extract_multiple_clips(
    input_video: str,
    clips: list[dict[str, Any]],
    output_dir: str,
    base_filename: str = "clip",
    generate_vertical: bool = False,
) -> list[dict[str, Any]]:
    """Extract horizontal (and optionally vertical) clips from a video.

    Each output dict gains ``path``, ``filename``, and optionally
    ``vertical_path`` / ``vertical_filename``.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    extracted = []
    for i, clip in enumerate(clips):
        start = clip["start"]
        end = clip["end"]
        duration = end - start
        fname = f"{base_filename}_{i + 1:03d}_{int(start)}s_{int(end)}s.mp4"
        fpath = out / fname

        try:
            extract_clip(input_video, start, duration, str(fpath))
        except Exception as e:
            logger.error("Error extracting clip %d: %s", i + 1, e)
            continue

        entry: dict[str, Any] = {**clip, "path": str(fpath), "filename": fname}

        if generate_vertical:
            vfname = f"{base_filename}_{i + 1:03d}_{int(start)}s_{int(end)}s_vertical.mp4"
            vfpath = out / vfname
            try:
                extract_vertical_clip(input_video, start, duration, str(vfpath))
                entry["vertical_path"] = str(vfpath)
                entry["vertical_filename"] = vfname
            except Exception as e:
                logger.error("Error extracting vertical clip %d: %s", i + 1, e)
                entry["vertical_path"] = None
                entry["vertical_filename"] = None

        extracted.append(entry)

    logger.info("Extracted %d / %d clips", len(extracted), len(clips))
    return extracted
