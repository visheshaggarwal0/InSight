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
    DebertaSentenceClassifier,scm-history-item:d%3A%5CDocuments%5CInSight?%7B%22repositoryId%22%3A%22scm0%22%2C%22historyItemId%22%3A%2218873aac19ea16d2b6f1f7d15a9a7f7d692a1961%22%2C%22historyItemParentId%22%3A%228c0e3cc80f7d9ea3d30ad987ccc7babd0efec868%22%2C%22historyItemDisplayId%22%3A%2218873aa%22%7D
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
