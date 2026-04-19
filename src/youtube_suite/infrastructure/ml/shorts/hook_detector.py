"""Hook detector — identifies high-impact moments in transcript segments without an LLM call."""
from __future__ import annotations

import re
from typing import Any

# Contradiction / surprise markers per language
_CONTRADICTION: dict[str, list[str]] = {
    "es": [r"\bpero\b", r"\bsin embargo\b", r"\baunque\b", r"\ba pesar\b", r"\bno obstante\b",
           r"\bresulta que\b", r"\blo curioso\b", r"\bparad[oa]jicamente\b"],
    "en": [r"\bbut\b", r"\bhowever\b", r"\balthough\b", r"\bdespite\b", r"\bnevertheless\b",
           r"\bactually\b", r"\bturns out\b", r"\bironically\b"],
    "fr": [r"\bmais\b", r"\bcependant\b", r"\bpourtant\b", r"\bn[eé]anmoins\b"],
    "de": [r"\baber\b", r"\bjedoch\b", r"\bdenno?ch\b", r"\ballerdings\b"],
    "pt": [r"\bmas\b", r"\bpor[eé]m\b", r"\bcontudo\b", r"\bno entanto\b"],
}

# Announcement / teaser markers per language
_ANNOUNCEMENT: dict[str, list[str]] = {
    "es": [r"\bos voy a\b", r"\bvoy a contar\b", r"\blo que nadie\b", r"\bsecreto\b",
           r"\brevelar\b", r"\bdescubrir\b", r"\bsorpresa\b", r"\bno te lo vas a creer\b",
           r"\bjam[aá]s\b", r"\bnunca antes\b"],
    "en": [r"\bi('m| am) going to\b", r"\blet me tell you\b", r"\bnobody knows\b",
           r"\bsecret\b", r"\breveal\b", r"\bdiscover\b", r"\byou won't believe\b",
           r"\bnever before\b"],
    "fr": [r"\bje vais vous\b", r"\bpersonne ne sait\b", r"\bsecret\b", r"\bjamais\b"],
    "de": [r"\bich werde\b", r"\bkeiner wei[sß]\b", r"\bgeheimnis\b", r"\bnoch nie\b"],
    "pt": [r"\bvou contar\b", r"\bningu[eé]m sabe\b", r"\bsegredo\b", r"\bnunca antes\b"],
}

_FALLBACK_LANG = "en"


def _patterns_for(lang: str, table: dict[str, list[str]]) -> list[str]:
    return table.get(lang, table.get(_FALLBACK_LANG, []))


def detect(text: str, language: str = "es") -> dict[str, Any]:
    """Detect hook type and score for a text segment.

    Returns a dict with keys:
        hook_type: "question" | "contradiction" | "announcement" | None
        hook_score: float 0-1
    """
    lang = language.split("-")[0].lower()  # "es-419" → "es"
    text_lower = text.lower()

    has_announcement = any(re.search(p, text_lower) for p in _patterns_for(lang, _ANNOUNCEMENT))
    if has_announcement:
        return {"hook_type": "announcement", "hook_score": 1.0}

    has_contradiction = any(re.search(p, text_lower) for p in _patterns_for(lang, _CONTRADICTION))
    if has_contradiction:
        return {"hook_type": "contradiction", "hook_score": 0.75}

    has_question = "?" in text
    if has_question:
        return {"hook_type": "question", "hook_score": 0.5}

    return {"hook_type": None, "hook_score": 0.0}
