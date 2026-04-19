"""ShortabilityScorer — custom RandomForest model that predicts viral potential of a clip segment."""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_scorer: Any = None

_FEATURE_ORDER = [
    "rms_energy",
    "zcr_mean",
    "spectral_centroid",
    "silence_ratio",
    "speech_rate",
    "semantic_score",
    "segment_position",
    "segment_duration",
    "speaker_changes",
    "question_marks",
    "exclamations",
    "hook_score",
]


def _model_path() -> Path:
    from youtube_suite.config.settings import get_settings

    models_dir = get_settings().cip_data_dir / "models"
    models_dir.mkdir(exist_ok=True)
    return models_dir / "shortability_scorer.pkl"


def _train(path: Path) -> Any:
    try:
        from sklearn.ensemble import RandomForestRegressor
    except ImportError:
        logger.warning("scikit-learn not installed — ShortabilityScorer unavailable")
        return None

    rng = np.random.RandomState(42)
    n = 8000

    X = rng.uniform(0, 1, (n, 12)).astype(float)
    # Realistic ranges for discrete/bounded features
    X[:, 7] = X[:, 7] * 25 + 5       # duration: 5-30s
    X[:, 8] = (X[:, 8] * 5).round()  # speaker_changes: 0-5
    X[:, 9] = (X[:, 9] * 3).round()  # question_marks: 0-3
    X[:, 10] = (X[:, 10] * 3).round()  # exclamations: 0-3

    rms, zcr, spectral, silence, speech_rate = X[:, 0], X[:, 1], X[:, 2], X[:, 3], X[:, 4]
    semantic, position, duration = X[:, 5], X[:, 6], X[:, 7]
    speaker_changes, questions, exclam, hook = X[:, 8], X[:, 9], X[:, 10], X[:, 11]

    y = (
        0.22 * rms                                      # high audio energy
        + 0.12 * zcr                                    # liveliness
        + 0.08 * spectral                               # audio brightness
        - 0.18 * silence                                # silence hurts
        + 0.08 * speech_rate                            # faster speech = more energy
        + 0.14 * semantic                               # semantic relevance
        + 0.10 * hook                                   # hook bonus
        + 0.06 * np.clip(questions / 3, 0, 1)           # rhetorical questions
        + 0.05 * np.clip(exclam / 3, 0, 1)              # exclamation energy
        + 0.04 * (1 - np.abs(position - 0.25))          # slight preference for early segments
        + 0.04 * (1 - np.abs(speaker_changes - 1.5) / 3)  # 1-2 speaker changes ideal
        - 0.03 * np.clip((duration - 15) / 15, 0, 1)   # mild penalty for very long clips
    )
    y = np.clip(y + rng.normal(0, 0.04, n), 0, 1)

    model = RandomForestRegressor(n_estimators=150, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X, y)

    with open(path, "wb") as f:
        pickle.dump(model, f)

    logger.info("ShortabilityScorer trained and saved → %s", path)
    return model


def _get_scorer() -> Any:
    global _scorer
    if _scorer is None:
        path = _model_path()
        if path.exists():
            with open(path, "rb") as f:
                _scorer = pickle.load(f)
            logger.info("ShortabilityScorer loaded from %s", path)
        else:
            logger.info("ShortabilityScorer not found — training…")
            _scorer = _train(path)
    return _scorer


def predict(features: dict[str, float]) -> float:
    """Return a shortability score in [0, 1] for a set of segment features."""
    scorer = _get_scorer()
    if scorer is None:
        # Fallback: simple heuristic if sklearn missing
        return float(np.clip(
            0.4 * features.get("rms_energy", 0.5)
            + 0.3 * features.get("semantic_score", 0.5)
            - 0.2 * features.get("silence_ratio", 0.3)
            + 0.1 * features.get("hook_score", 0.0),
            0, 1,
        ))

    row = np.array([features.get(k, 0.5) for k in _FEATURE_ORDER], dtype=float).reshape(1, -1)
    # Restore realistic scale for duration (stored as seconds, not 0-1)
    row[0, 7] = features.get("segment_duration", 15.0)
    row[0, 8] = features.get("speaker_changes", 0)
    row[0, 9] = features.get("question_marks", 0)
    row[0, 10] = features.get("exclamations", 0)

    return float(np.clip(scorer.predict(row)[0], 0, 1))
