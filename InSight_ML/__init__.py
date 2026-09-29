"""InSight_ML backward-compatibility package initializer.
All core machine learning primitives now live natively in backend/app/ml/.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import app.ml as ml
