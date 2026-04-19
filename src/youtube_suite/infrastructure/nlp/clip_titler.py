"""LLM-powered clip titler — generates viral titles and hashtags for short clips."""
from __future__ import annotations

import json
import logging
import re

import anthropic

from youtube_suite.config.settings import get_settings

logger = logging.getLogger(__name__)

_LANGUAGE_NAMES: dict[str, str] = {
    "es": "Spanish", "en": "English", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese",
}

_SYSTEM = (
    "You are a viral social-media content expert specialising in YouTube Shorts and TikTok. "
    "You create punchy, curiosity-driven titles and relevant hashtags that maximise watch time. "
    "Return only valid JSON — no markdown, no extra text."
)


def generate_clip_title(
    clip_text: str,
    *,
    language: str = "es",
    hook_type: str | None = None,
    video_title: str | None = None,
) -> dict[str, str | list[str]]:
    """Generate a viral title and hashtags for a short clip via Claude.

    Returns:
        {"title": str, "hashtags": ["#tag1", ...]}
    Raises:
        ValueError: if ANTHROPIC_API_KEY is not configured.
    """
    s = get_settings()
    if not s.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    lang_name = _LANGUAGE_NAMES.get(language.split("-")[0].lower(), language)
    hook_hint = f"This clip contains a {hook_type} — leverage that tension." if hook_type else ""
    title_hint = f'Context — full video title: "{video_title}".' if video_title else ""

    user = (
        f"Create a viral title and 5 hashtags for this {lang_name} short clip.\n"
        f"{title_hint}\n{hook_hint}\n\n"
        f"Clip transcript:\n{clip_text[:800]}\n\n"
        "Rules:\n"
        f"- Title: max 60 characters, in {lang_name}, punchy and curiosity-driven.\n"
        "- Hashtags: 5 items, no spaces inside each tag.\n"
        '- Return: {"title": "...", "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]}'
    )

    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    response = client.messages.create(
        model=s.anthropic_model,
        max_tokens=200,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    raw = next((b.text for b in response.content if b.type == "text"), "{}")

    # Extract first JSON object from response
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return {
                "title": str(data.get("title", "")),
                "hashtags": list(data.get("hashtags", [])),
            }
        except json.JSONDecodeError:
            logger.warning("Could not parse clip titler response: %s", raw[:200])

    return {"title": "", "hashtags": []}
