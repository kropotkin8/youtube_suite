"""Highlight detection — semantic segmentation + multi-feature scoring."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util

from youtube_suite.config.settings import get_settings

logger = logging.getLogger(__name__)

_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        name = get_settings().embedding_model
        logger.info("Loading embedding model: %s", name)
        _embedding_model = SentenceTransformer(name)
    return _embedding_model


# ---------------------------------------------------------------------------
# Semantic segmentation
# ---------------------------------------------------------------------------

def generate_candidate_segments(
    transcription_segments: list[dict[str, Any]],
    min_duration: float | None = None,
    max_duration: float | None = None,
    target_duration: float | None = None,
) -> list[dict[str, Any]]:
    """Segment transcript into candidates using semantic coherence + duration constraints.

    Uses cosine-similarity between adjacent segment embeddings to detect topic
    boundaries instead of naively grouping by elapsed time.
    """
    s = get_settings()
    min_dur = min_duration or s.min_clip_duration
    max_dur = max_duration or s.max_clip_duration
    target_dur = target_duration or s.target_clip_duration

    if not transcription_segments:
        return []

    model = get_embedding_model()

    texts = [seg["text"].strip() for seg in transcription_segments]
    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

    # Compute cosine similarity between consecutive segments
    boundary_flags = [False]  # first segment never starts a new boundary by default
    for i in range(1, len(transcription_segments)):
        sim = util.cos_sim(embeddings[i - 1], embeddings[i]).item()
        # A drop below 0.35 signals a topic shift
        boundary_flags.append(sim < 0.35)

    # Group segments separated by boundaries into candidate windows
    raw_groups: list[list[dict]] = []
    current: list[dict] = []
    for seg, is_boundary in zip(transcription_segments, boundary_flags):
        if is_boundary and current:
            raw_groups.append(current)
            current = []
        current.append(seg)
    if current:
        raw_groups.append(current)

    # Convert groups → candidate dicts respecting min/max duration
    candidates: list[dict[str, Any]] = []
    for group in raw_groups:
        candidates.extend(_split_group(group, min_dur, max_dur, target_dur))

    logger.info("Generated %d candidate segments (semantic segmentation)", len(candidates))
    return candidates


def _split_group(
    segs: list[dict],
    min_dur: float,
    max_dur: float,
    target_dur: float,
) -> list[dict]:
    """Split a semantically coherent group into chunks that respect duration limits."""
    result = []
    current_segs: list[dict] = []
    current_start = segs[0]["start"]

    for seg in segs:
        current_segs.append(seg)
        elapsed = seg["end"] - current_start

        if elapsed >= target_dur or elapsed >= max_dur:
            if elapsed >= min_dur:
                result.append(_merge_segs(current_segs))
            current_segs = []
            current_start = seg["end"]

    if current_segs:
        elapsed = current_segs[-1]["end"] - current_start
        if elapsed >= min_dur:
            result.append(_merge_segs(current_segs))

    return result


def _merge_segs(segs: list[dict]) -> dict:
    words: list = []
    for s in segs:
        words.extend(s.get("words", []))
    return {
        "text": " ".join(s["text"] for s in segs),
        "start": segs[0]["start"],
        "end": segs[-1]["end"],
        "words": words,
        "speaker": segs[0].get("speaker"),
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _semantic_score(candidate_text: str, full_transcript: str, model: SentenceTransformer) -> float:
    try:
        cand_emb = model.encode(candidate_text, convert_to_tensor=True)
        chunk_size = 500
        chunks = [full_transcript[i: i + chunk_size] for i in range(0, len(full_transcript), chunk_size)]
        chunk_embs = model.encode(chunks, convert_to_tensor=True)
        doc_emb = torch.mean(chunk_embs, dim=0)
        sim = util.cos_sim(cand_emb.unsqueeze(0), doc_emb.unsqueeze(0)).item()
        return float((sim + 1) / 2)
    except Exception as e:
        logger.warning("semantic_score error: %s", e)
        return 0.5


def _speaker_change_score(candidate: dict, all_segs: list[dict]) -> float:
    if not candidate.get("speaker"):
        return 0.3
    cs, ce = candidate["start"], candidate["end"]
    before = {s["speaker"] for s in all_segs if s["end"] <= cs and abs(s["end"] - cs) < 3 and s.get("speaker")}
    after = {s["speaker"] for s in all_segs if s["start"] >= ce and abs(s["start"] - ce) < 3 and s.get("speaker")}
    if (before and candidate["speaker"] not in before) or (after and candidate["speaker"] not in after):
        return 1.0
    return 0.5


def score_candidates(
    candidates: list[dict[str, Any]],
    full_transcript: str,
    audio_path: str | None = None,
    audio_duration: float = 0.0,
    language: str = "es",
) -> list[dict[str, Any]]:
    """Score candidates using ShortabilityScorer + semantic + hook + speaker-change.

    Each candidate gains:
        score: float (final weighted score)
        score_breakdown: {semantic, audio_energy, speaker_change, hook_score, shortability}
        hook_type: str | None
    """
    from youtube_suite.infrastructure.ml.shorts import hook_detector, shortability_scorer
    from youtube_suite.infrastructure.ml.shorts.audio_service import analyze_audio_features

    model = get_embedding_model()
    w = get_settings().score_weights

    scored = []
    for cand in candidates:
        words = cand.get("words", [])
        text = cand["text"]
        start, end = cand["start"], cand["end"]
        duration = end - start

        # --- Semantic ---
        sem = _semantic_score(text, full_transcript, model)

        # --- Speaker change ---
        spk = _speaker_change_score(cand, candidates)

        # --- Hook ---
        hook_info = hook_detector.detect(text, language=language)
        hook_score = hook_info["hook_score"]
        hook_type = hook_info["hook_type"]

        # --- Real audio features ---
        if audio_path:
            audio_feats = analyze_audio_features(audio_path, start, end)
        else:
            audio_feats = {"rms_energy": 0.5, "zcr_mean": 0.5, "spectral_centroid": 0.5, "silence_ratio": 0.3}

        # --- Speech rate (words/second, normalised) ---
        word_count = len(words) if words else len(text.split())
        speech_rate = float(np.clip(word_count / max(duration, 1) / 4, 0, 1))

        # --- Segment position in video ---
        position = float(start / audio_duration) if audio_duration > 0 else 0.5

        # --- Discrete counts ---
        question_marks = min(text.count("?"), 3)
        exclamations = min(text.count("!"), 3)
        speaker_changes = sum(
            1 for i in range(1, len(words))
            if words[i].get("speaker") != words[i - 1].get("speaker")
        ) if len(words) > 1 else 0

        # --- ShortabilityScorer ---
        features = {
            **audio_feats,
            "speech_rate": speech_rate,
            "semantic_score": sem,
            "segment_position": position,
            "segment_duration": duration,
            "speaker_changes": speaker_changes,
            "question_marks": question_marks,
            "exclamations": exclamations,
            "hook_score": hook_score,
        }
        shortability = shortability_scorer.predict(features)

        # --- Final weighted score ---
        total = (
            w["shortability"] * shortability
            + w["semantic"] * sem
            + w["hook"] * hook_score
            + w["speaker_change"] * spk
        )

        scored.append({
            **cand,
            "score": float(total),
            "score_breakdown": {
                "semantic": round(sem, 4),
                "audio_energy": round(audio_feats["rms_energy"], 4),
                "speaker_change": round(spk, 4),
                "hook_score": round(hook_score, 4),
                "shortability": round(shortability, 4),
                "silence_ratio": round(audio_feats["silence_ratio"], 4),
            },
            "hook_type": hook_type,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    logger.info("Scored %d candidates", len(scored))
    return scored


def select_top_clips(
    scored_candidates: list[dict[str, Any]],
    num_clips: int | None = None,
) -> list[dict[str, Any]]:
    """Select top N non-overlapping clips (5s margin between clips)."""
    num_clips = num_clips or get_settings().num_clips
    selected: list[dict] = []
    used: list[tuple[float, float]] = []

    for cand in scored_candidates:
        if len(selected) >= num_clips:
            break
        start, end = cand["start"], cand["end"]
        if any(not (end < us - 5 or start > ue + 5) for us, ue in used):
            continue
        selected.append(cand)
        used.append((start, end))

    logger.info("Selected %d / %d candidates", len(selected), len(scored_candidates))
    return selected


def rescore_with_weights(
    clips: list[dict[str, Any]],
    weights: dict[str, float],
) -> list[dict[str, Any]]:
    """Re-weight existing scored clips without re-running the pipeline.

    Expects each clip to have a ``score_breakdown`` dict.
    Returns clips re-sorted by new total score.
    """
    w_short = weights.get("shortability", 0.5)
    w_sem = weights.get("semantic", 0.2)
    w_hook = weights.get("hook", 0.1)
    w_spk = weights.get("speaker_change", 0.1)

    rescored = []
    for clip in clips:
        bd = clip.get("score_breakdown", {})
        total = (
            w_short * bd.get("shortability", 0.5)
            + w_sem * bd.get("semantic", 0.5)
            + w_hook * bd.get("hook_score", 0.0)
            + w_spk * bd.get("speaker_change", 0.3)
        )
        rescored.append({**clip, "score": float(total)})

    rescored.sort(key=lambda x: x["score"], reverse=True)
    return rescored
