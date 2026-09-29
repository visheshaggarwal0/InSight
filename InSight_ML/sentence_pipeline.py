"""InSight_ML.sentence_pipeline backward-compatibility shim.
The canonical implementation has moved to backend/app/ml/sentence_pipeline.py.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.ml.sentence_pipeline import (
    LABEL_COMPLAINT,
    LABEL_RECOMMENDATION,
    LABEL_PRAISE_NOISE,
    SentenceRecord,
    RoutedPools,
    DebertaSentenceClassifier,
    deconstruct_sentences,
    classify_and_route_review,
    classify_and_route_corpus,
    _classify_sentence,
    _COMPLAINT_PATTERN,
    _RECOMMENDATION_PATTERN,
    _PRAISE_PATTERN,
    _NEGATION_FILTER,
)

__all__ = [
    "LABEL_COMPLAINT",
    "LABEL_RECOMMENDATION",
    "LABEL_PRAISE_NOISE",
    "SentenceRecord",
    "RoutedPools",
    "DebertaSentenceClassifier",
    "deconstruct_sentences",
    "classify_and_route_review",
    "classify_and_route_corpus",
    "_classify_sentence",
    "_COMPLAINT_PATTERN",
    "_RECOMMENDATION_PATTERN",
    "_PRAISE_PATTERN",
    "_NEGATION_FILTER",
]
