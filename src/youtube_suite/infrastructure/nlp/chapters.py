from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Callable

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer, util as st_util
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False
    SentenceTransformer = None  # type: ignore[assignment,misc]
    st_util = None  # type: ignore[assignment]

_embedding_model: "SentenceTransformer | None" = None


def _get_embedding_model(name: str) -> "SentenceTransformer":
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model for chapters: %s", name)
        _embedding_model = SentenceTransformer(name)
    return _embedding_model


def _build_windows(
    segments: list[dict],
    window_sec: float,
    overlap_sec: float,
) -> list[dict]:
    if not segments:
        return []

    step = max(window_sec - overlap_sec, 1.0)
    video_end = float(segments[-1]["end_time"])
    windows: list[dict] = []
    t = 0.0
    while t < video_end:
        w_end = t + window_sec
        included = [
            (i, s) for i, s in enumerate(segments)
            if float(s["start_time"]) < w_end and float(s["end_time"]) > t
        ]
        if included:
            idxs = [i for i, _ in included]
            text = " ".join(s["text"].strip() for _, s in included)
            windows.append({"start": t, "end": min(w_end, video_end), "text": text, "segment_indices": idxs})
        t += step

    return windows


def _detect_boundaries_semantic(
    windows: list[dict],
    threshold: float,
    embedding_model_name: str,
) -> list[int]:
    if len(windows) <= 1:
        return [0] if windows else []

    model = _get_embedding_model(embedding_model_name)
    texts = [w["text"] for w in windows]
    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

    boundaries = [0]
    for i in range(1, len(windows)):
        sim = st_util.cos_sim(embeddings[i - 1], embeddings[i]).item()
        if sim < threshold:
            boundaries.append(i)

    return boundaries


def _detect_boundaries_naive(windows: list[dict]) -> list[int]:
    return list(range(len(windows)))


def _windows_to_chapters(
    windows: list[dict],
    boundary_indices: set[int],
    segments: list[dict],
) -> list[dict]:
    chapters: list[dict] = []
    boundary_list = sorted(boundary_indices)

    for b_idx, b_start in enumerate(boundary_list):
        b_end = boundary_list[b_idx + 1] if b_idx + 1 < len(boundary_list) else len(windows)
        chapter_windows = windows[b_start:b_end]
        if not chapter_windows:
            continue

        all_seg_idxs: set[int] = set()
        for w in chapter_windows:
            all_seg_idxs.update(w["segment_indices"])
        sorted_idxs = sorted(all_seg_idxs)

        if not sorted_idxs:
            continue

        start_sec = float(segments[sorted_idxs[0]]["start_time"])
        end_sec = float(segments[sorted_idxs[-1]]["end_time"])
        text = " ".join(segments[i]["text"].strip() for i in sorted_idxs)
        chapters.append({"start_seconds": start_sec, "end_seconds": end_sec, "text": text})

    return chapters


def _merge_short_chapters(chapters: list[dict], min_duration: float) -> list[dict]:
    if not chapters:
        return []

    merged = [chapters[0].copy()]
    for ch in chapters[1:]:
        if (ch["end_seconds"] - ch["start_seconds"]) < min_duration:
            merged[-1]["end_seconds"] = ch["end_seconds"]
            merged[-1]["text"] = merged[-1]["text"] + " " + ch["text"]
        else:
            merged.append(ch.copy())

    return merged


_STOP_WORDS = frozenset(
    "el la los las un una de del en y a con para que se es son por lo le "
    "nos al como más pero si su sus este esta estos estas ese esa".split()
)


def _extractive_title(text: str, max_chars: int) -> str:
    match = re.search(r"[.!?]", text)
    first_sentence = text[: match.start()].strip() if match else text.strip()
    words = [w for w in first_sentence.split() if w.lower().rstrip(".,!?") not in _STOP_WORDS]
    title = ""
    for w in words:
        candidate = (title + " " + w).strip() if title else w
        if len(candidate) > max_chars:
            break
        title = candidate
    return title or text[:max_chars].strip()


def _generate_titles_claude(
    chapters: list[dict],
    *,
    api_key: str,
    model: str,
    max_chars: int,
    progress_callback: Callable[[float, str], None] | None,
) -> list[str]:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    titles: list[str] = []
    n = len(chapters)

    for i, ch in enumerate(chapters):
        if progress_callback:
            progress_callback(0.60 + 0.35 * (i / n), f"Generando título {i + 1}/{n}…")

        text_sample = ch["text"][:600]
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=80,
                system="You are a YouTube chapter title expert. Return only the chapter title — no quotes, no explanation.",
                messages=[{
                    "role": "user",
                    "content": (
                        f"Generate a concise, engaging YouTube chapter title (max {max_chars} characters) "
                        f"for the following transcript excerpt. Return ONLY the title text.\n\nTranscript:\n{text_sample}"
                    ),
                }],
            )
            raw = next((b.text for b in resp.content if b.type == "text"), "").strip()
            titles.append(raw[:max_chars].strip())
        except Exception:
            logger.warning("Claude title generation failed for chapter %d", i, exc_info=True)
            titles.append(_extractive_title(ch["text"], max_chars))

    return titles


def _format_seconds(total: float) -> str:
    total_int = int(total)
    h = total_int // 3600
    m = (total_int % 3600) // 60
    s = total_int % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _build_youtube_format(chapters: list[dict]) -> str:
    return "\n".join(f"{_format_seconds(ch['start_seconds'])} {ch['title']}" for ch in chapters)


def generate_chapters(
    segments: list[dict],
    *,
    progress_callback: Callable[[float, str], None] | None = None,
) -> dict:
    from youtube_suite.config.settings import get_settings
    s = get_settings()

    def _cb(frac: float, msg: str) -> None:
        if progress_callback:
            progress_callback(frac, msg)

    if not segments:
        raise ValueError("No transcript segments provided")

    segments = sorted(segments, key=lambda x: float(x["start_time"]))

    _cb(0.05, "Agrupando segmentos en ventanas…")
    windows = _build_windows(segments, window_sec=s.chapter_window_seconds, overlap_sec=s.chapter_window_overlap_seconds)

    if not windows:
        raise ValueError("Could not build windows from segments — video too short?")

    _cb(0.20, "Detectando cambios de tema…")
    if _ST_AVAILABLE:
        boundary_indices = _detect_boundaries_semantic(windows, threshold=s.chapter_similarity_threshold, embedding_model_name=s.embedding_model)
        titling_method = "extractive"
    else:
        logger.warning("sentence-transformers not available — using naive chapter segmentation")
        boundary_indices = _detect_boundaries_naive(windows)
        titling_method = "naive_extractive"

    _cb(0.40, "Ensamblando capítulos…")
    chapters = _windows_to_chapters(windows, set(boundary_indices), segments)

    if not chapters:
        raise ValueError("No chapters could be generated from the transcript")

    _cb(0.50, "Fusionando capítulos cortos…")
    chapters = _merge_short_chapters(chapters, min_duration=s.chapter_min_duration)

    if len(chapters) == 1:
        logger.warning("Only one chapter detected — video may be semantically uniform")

    chapters[0]["start_seconds"] = 0.0

    _cb(0.60, "Generando títulos de capítulos…")
    if s.anthropic_api_key:
        titles = _generate_titles_claude(
            chapters,
            api_key=s.anthropic_api_key,
            model=s.anthropic_model,
            max_chars=s.chapter_max_title_chars,
            progress_callback=progress_callback,
        )
        titling_method = "claude"
    else:
        titles = [_extractive_title(ch["text"], s.chapter_max_title_chars) for ch in chapters]

    for ch, title in zip(chapters, titles):
        ch["title"] = title or _extractive_title(ch["text"], s.chapter_max_title_chars)

    _cb(0.98, "Formateando salida…")
    youtube_format = _build_youtube_format(chapters)

    return {
        "chapter_count": len(chapters),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "youtube_format": youtube_format,
        "titling_method": titling_method,
        "chapters": [
            {
                "start_seconds": ch["start_seconds"],
                "end_seconds": ch["end_seconds"],
                "title": ch["title"],
                "text": ch["text"][:300],
            }
            for ch in chapters
        ],
    }
