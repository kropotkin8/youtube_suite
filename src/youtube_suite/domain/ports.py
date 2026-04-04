from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class ASRSegment:
    start: float
    end: float
    text: str


class TranscriptionPort(Protocol):
    def transcribe(self, audio_path: Path) -> tuple[list[ASRSegment], str]: ...


class FileStoragePort(Protocol):
    def save_upload(self, filename: str, data: bytes) -> tuple[str, Path]: ...

    def path_for_key(self, storage_key: str) -> Path: ...
