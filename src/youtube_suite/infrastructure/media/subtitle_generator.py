from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Iterable


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


def _format_timestamp(seconds: float) -> str:
    """Convert a duration in seconds to an SRT timestamp string (``HH:MM:SS,mmm``).

    Args:
        seconds: Non-negative duration in seconds.

    Returns:
        SRT-formatted timestamp string.
    """
    if seconds < 0:
        seconds = 0
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    millis = int((td.total_seconds() - total_seconds) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def segments_to_srt(segments: Iterable[TranscriptSegment], output_path: Path) -> Path:
    """Write an iterable of transcript segments to an SRT subtitle file.

    Empty segments are skipped. The resulting file uses UTF-8 encoding.

    Args:
        segments: Iterable of ``TranscriptSegment`` objects with start, end, and text.
        output_path: Destination path for the generated ``.srt`` file.

    Returns:
        Path to the written SRT file.
    """
    output_path = Path(output_path)
    lines: list[str] = []
    for idx, segment in enumerate(segments, start=1):
        start_ts = _format_timestamp(segment.start)
        end_ts = _format_timestamp(segment.end)
        text = (segment.text or "").strip()
        if not text:
            continue
        lines.append(str(idx))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(text)
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
