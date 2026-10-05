"""complaint_extraction.py
Standalone complaint extraction utility for InSight ML pipeline.

Uses the unified sentence and clause intent extractor with exact character
offset and bounded proposition guarantees, eliminating greedy multi-sentence capture
and filtering mitigated/negated expressions (e.g. 'no breakouts', 'zero irritation').

Returns a dictionary with:
  detected : bool   – True if a complaint pattern was found
  text     : str    – the matched span (empty string if not detected)
  start    : int    – start character offset (None if not detected)
  end      : int    – end character offset (None if not detected)
  trigger  : str    – 'pattern' when detected, else None
"""

from typing import Dict, Any
from app.ml.sentence_pipeline import sentence_clause_extractor


def extract_complaint_span(text: str) -> Dict[str, Any]:
    """Extract a complaint clause from *text* using bounded proposition parsing.

    Guarantees:
        text[start:end] == span_text   # when detected is True
    """
    if not isinstance(text, str) or not text.strip():
        return {"detected": False, "text": "", "start": None, "end": None, "trigger": None}

    span = sentence_clause_extractor.extract_complaint_span(text)
    if span.detected:
        return {
            "detected": True,
            "text": span.text,
            "start": span.start,
            "end": span.end,
            "trigger": "pattern",
        }
    return {
        "detected": False,
        "text": "",
        "start": None,
        "end": None,
        "trigger": None,
    }


__all__ = ["extract_complaint_span"]
