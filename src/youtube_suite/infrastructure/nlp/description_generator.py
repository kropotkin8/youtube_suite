from __future__ import annotations

from typing import Iterable

import anthropic

from youtube_suite.config.settings import get_settings

# Map BCP-47 language codes to human-readable names for the prompt
_LANGUAGE_NAMES: dict[str, str] = {
    "es": "Spanish",
    "en": "English",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
}


def _build_prompts(
    transcript_text: str,
    trending_keywords: Iterable[str] | None = None,
    *,
    title: str | None = None,
    language: str = "es",
) -> tuple[str, str]:
    """Return (system_content, user_content) for the description generation prompt."""
    language_name = _LANGUAGE_NAMES.get(language.lower(), language)
    keywords_str = ", ".join(trending_keywords or [])

    system_content = (
        "You are an expert YouTube content strategist. "
        "You write professional, engaging, and SEO-optimised video descriptions that look natural on YouTube. "
        "Follow standard YouTube description structure: hook paragraph, key topics covered, relevant hashtags. "
        "Never mention that the text comes from a transcript. Never copy transcript sentences verbatim."
    )

    user_content = f"Write a YouTube video description in {language_name} for the following video.\n\n"
    if title:
        user_content += f"Title: {title}\n\n"
    if keywords_str:
        user_content += f"Trending keywords to incorporate naturally: {keywords_str}\n\n"
    user_content += (
        f"Video transcript (use this as the content source — do not copy sentences verbatim):\n{transcript_text}\n\n"
        "Requirements:\n"
        "- Start with a compelling 2-3 sentence hook that summarises what viewers will learn or enjoy.\n"
        "- List 4-6 key topics covered using bullet points (e.g. '• Topic one').\n"
        "- End with 3-5 relevant hashtags.\n"
        "- Integrate the trending keywords naturally where appropriate.\n"
        f"- Write entirely in {language_name}. Do not translate or mix languages.\n"
        "- Return only the final description text, ready to paste into YouTube."
    )
    return system_content, user_content


def generate_video_description(
    transcript_text: str,
    trending_keywords: Iterable[str] | None = None,
    *,
    title: str | None = None,
    language: str = "es",
) -> str:
    """Generate a professional YouTube description via the Anthropic Claude API.

    Args:
        transcript_text: Full transcript of the video used as the content source.
        trending_keywords: Optional iterable of trending keywords to incorporate.
        title: Optional video title to provide additional context to the model.
        language: BCP-47 language code for the output description (default: "es").

    Returns:
        Generated description text ready to paste into YouTube.

    Raises:
        ValueError: If ``ANTHROPIC_API_KEY`` is not configured in settings.
    """
    s = get_settings()
    if not s.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    system_content, user_content = _build_prompts(
        transcript_text, trending_keywords, title=title, language=language
    )

    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    response = client.messages.create(
        model=s.anthropic_model,
        max_tokens=1000,
        system=system_content,
        messages=[{"role": "user", "content": user_content}],
    )
    content = next((block.text for block in response.content if block.type == "text"), "")
    return content.strip()
