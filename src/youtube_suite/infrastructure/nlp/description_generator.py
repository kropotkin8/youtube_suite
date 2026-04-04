from __future__ import annotations

from typing import Iterable

from openai import OpenAI

from youtube_suite.config.settings import get_settings


def generate_video_description(
    transcript_text: str,
    trending_keywords: Iterable[str] | None = None,
    *,
    title: str | None = None,
) -> str:
    """Generate an SEO-optimised Spanish YouTube description via the OpenAI Chat API.

    Args:
        transcript_text: Full transcript of the video used as the primary content source.
        trending_keywords: Optional iterable of trending keywords to incorporate.
        title: Optional video title to provide additional context to the model.

    Returns:
        Generated description text ready to paste into YouTube.

    Raises:
        ValueError: If ``OPENAI_API_KEY`` is not configured in settings.
    """
    s = get_settings()
    if not s.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured")
    keywords_str = ", ".join(trending_keywords or [])
    system_content = (
        "Eres un asistente experto en marketing de contenidos en YouTube. "
        "Escribes descripciones claras, concisas y muy optimizadas para SEO en español neutro."
    )
    user_content = (
        "Genera una descripción optimizada para SEO para un video de YouTube en español.\n\n"
    )
    if title:
        user_content += f"Título del video: {title}\n\n"
    if keywords_str:
        user_content += f"Palabras clave de tendencia: {keywords_str}\n\n"
    user_content += (
        "Transcripción:\n\n"
        f"{transcript_text}\n\n"
        "Devuelve solo la descripción final lista para pegar en YouTube."
    )
    client = OpenAI(api_key=s.openai_api_key)
    response = client.chat.completions.create(
        model=s.openai_model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
        max_tokens=600,
    )
    content = response.choices[0].message.content or ""
    return content.strip()
