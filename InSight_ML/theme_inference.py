"""InSight_ML.theme_inference backward-compatibility shim.
The canonical implementation has moved to backend/app/ml/theme_inference.py.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.ml.theme_inference import (
    ThemeInferenceEngine,
    get_theme_engine,
)

__all__ = [
    "ThemeInferenceEngine",
    "get_theme_engine",
]
