"""InSight_ML.validation backward-compatibility shim.
The canonical implementation has moved to backend/app/ml/validation.py.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.ml.validation import (
    validate_cosmetics_df,
    validate_custom_csv,
    verify_complaint_spans,
    ValidationResult,
    Issue,
    ValidationIssue,
)

__all__ = [
    "validate_cosmetics_df",
    "validate_custom_csv",
    "verify_complaint_spans",
    "ValidationResult",
    "Issue",
    "ValidationIssue",
]
