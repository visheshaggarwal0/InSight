"""InSight_ML.complaint_extraction backward-compatibility shim.
The canonical implementation has moved to backend/app/ml/complaint_extraction.py.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.ml.complaint_extraction import (
    extract_complaint_span,
    _PATTERN,
)

__all__ = [
    "extract_complaint_span",
    "_PATTERN",
]
