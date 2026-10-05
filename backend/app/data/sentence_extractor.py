"""sentence_extractor.py
Surgical Sentence Deconstructor & Clause-Level Defect Span Extractor for InSight.

This module unifies with and re-exports from ``app.ml.sentence_pipeline``, providing
a single source of truth across the entire platform for:
  - Exact character offset guarantee: text[start:end] == span_text
  - Sentence Boundary Disambiguation (SBD) protecting abbreviations and versions
  - Four-Tier Operational Severity Tagging (P0 to P3)
  - Proposition routing (COMPLAINT, RECOMMENDATION, PRAISE_NOISE)
  - Bounded complaint clause extraction for dense vector embeddings
"""

from __future__ import annotations

from app.ml.sentence_pipeline import (
    SentenceClauseExtractor,
    sentence_clause_extractor,
    SentenceProposition,
    HighlightSpan,
    ExtractedReviewTelemetry,
    CLASS_COMPLAINT,
    CLASS_RECOMMENDATION,
    CLASS_PRAISE_NOISE,
    SEVERITY_P0,
    SEVERITY_P1,
    SEVERITY_P2,
    SEVERITY_P3,
    evaluate_severity,
)

__all__ = [
    "SentenceClauseExtractor",
    "SentenceProposition",
    "HighlightSpan",
    "ExtractedReviewTelemetry",
    "sentence_clause_extractor",
    "CLASS_COMPLAINT",
    "CLASS_RECOMMENDATION",
    "CLASS_PRAISE_NOISE",
    "SEVERITY_P0",
    "SEVERITY_P1",
    "SEVERITY_P2",
    "SEVERITY_P3",
    "evaluate_severity",
]
