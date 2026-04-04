from __future__ import annotations

from typing import Any

from dateutil import parser as date_parser


def _parse_datetime(s: str | None) -> object | None:
    """Parse an ISO 8601 datetime string, returning ``None`` on failure or empty input.

    Args:
        s: ISO 8601 datetime string or ``None``.

    Returns:
        Parsed ``datetime`` object, or ``None`` if the input is blank or unparseable.
    """
    if not s:
        return None
    try:
        return date_parser.isoparse(s)
    except Exception:
        return None


def _sanitize(value: str | None) -> str | None:
    """Strip null bytes that PostgreSQL rejects from text fields."""
    if value is None:
        return None
    return value.replace("\x00", "")


def transform_comment(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise a raw comment dict (as produced by the extract layer) for database insertion.

    Parses the ``published_at`` field from a string to a ``datetime`` if needed.

    Args:
        raw: Raw comment dict with keys such as ``comment_id``, ``video_id``, ``author``, etc.

    Returns:
        Normalised dict with database-ready fields.
    """
    out = {
        "comment_id": raw.get("comment_id"),
        "video_id": raw.get("video_id"),
        "author": _sanitize(raw.get("author")),
        "text": _sanitize(raw.get("text")),
        "published_at": raw.get("published_at"),
        "like_count": int(raw.get("like_count", 0)) if raw.get("like_count") is not None else 0,
        "parent_id": raw.get("parent_id"),
        "raw_snippet": raw.get("raw_snippet"),
    }
    if isinstance(out["published_at"], str):
        out["published_at"] = _parse_datetime(out["published_at"])
    return out


def transform_comments(raw_list: list[dict]) -> list[dict]:
    """Normalise a list of raw comment dicts, skipping those without a ``comment_id``.

    Args:
        raw_list: List of raw comment dicts from the extract layer.

    Returns:
        List of normalised comment dicts ready for database insertion.
    """
    return [transform_comment(c) for c in raw_list if c.get("comment_id")]
