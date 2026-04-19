from __future__ import annotations

from typing import Iterable

import ollama

from youtube_suite.config.settings import get_settings
from youtube_suite.infrastructure.nlp.description_generator import _build_prompts


def generate_video_description_local(
    transcript_text: str,
    trending_keywords: Iterable[str] | None = None,
    *,
    title: str | None = None,
    language: str = "es",
) -> str:
    """Generate a professional YouTube description using a local Ollama LLM.

    Args:
        transcript_text: Full transcript of the video used as the content source.
        trending_keywords: Optional iterable of trending keywords to incorporate.
        title: Optional video title to provide additional context to the model.
        language: BCP-47 language code for the output description (default: "es").

    Returns:
        Generated description text ready to paste into YouTube.

    Raises:
        RuntimeError: If the Ollama daemon is not reachable.
    """
    s = get_settings()
    system_content, user_content = _build_prompts(
        transcript_text, trending_keywords, title=title, language=language
    )
    try:
        client = ollama.Client(host=s.local_llm_base_url)
        response = client.chat(
            model=s.local_llm_model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )
        return response.message.content.strip()
    except Exception as exc:
        if "connection" in str(exc).lower() or "refused" in str(exc).lower():
            raise RuntimeError(
                f"Ollama not reachable at {s.local_llm_base_url}. Run `ollama serve` first."
            ) from exc
        raise
