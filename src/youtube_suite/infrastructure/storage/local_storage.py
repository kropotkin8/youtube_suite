from __future__ import annotations

import uuid
from pathlib import Path

from youtube_suite.config.settings import get_settings
from youtube_suite.domain.ports import FileStoragePort


class LocalFileStorage(FileStoragePort):
    def __init__(self, base: Path | None = None) -> None:
        self.base = base or (get_settings().cip_data_dir / "uploads")

    def save_upload(self, filename: str, data: bytes) -> tuple[str, Path]:
        """Write raw bytes to a UUID-keyed file under the uploads directory.

        Args:
            filename: Original filename used to derive the file extension.
            data: Raw file bytes to persist.

        Returns:
            Tuple of (storage key, absolute path to the saved file).
        """
        self.base.mkdir(parents=True, exist_ok=True)
        ext = Path(filename).suffix or ".bin"
        key = f"{uuid.uuid4()}{ext}"
        path = self.base / key
        path.write_bytes(data)
        return key, path

    def path_for_key(self, storage_key: str) -> Path:
        """Resolve the absolute filesystem path for a given storage key.

        Args:
            storage_key: Key returned by ``save_upload``.

        Returns:
            Absolute path under the uploads directory.
        """
        return self.base / storage_key
