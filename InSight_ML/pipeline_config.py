"""InSight_ML.pipeline_config backward-compatibility shim.
The canonical implementation has moved to backend/app/ml/pipeline_config.py.

This module used to be a byte-identical SECOND COPY of the canonical file.
Two live copies of every threshold and path is exactly the failure mode this
monorepo is being refactored away from: a fix applied here was invisible to
scripts/run_pipeline.py and backend/app/ml/sentence_pipeline.py (which import
the canonical copy), and vice versa. It is now a pure re-export, so there is
exactly one definition of every threshold in the repository.

Import ``InSight_ML.pipeline_config`` to keep old callers working; new code
should import ``app.ml.pipeline_config`` directly.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Re-export the canonical module's entire public surface (see its __all__).
from app.ml.pipeline_config import *  # noqa: F401,F403

# ``_find_project_root`` is private, so a star import does not carry it over,
# but it was importable from this module before the shim existed. Keep it
# reachable so no caller breaks.
from app.ml.pipeline_config import _find_project_root  # noqa: F401

# Keep this module's own __all__ in sync with the canonical module, so that
# ``from InSight_ML.pipeline_config import *`` stays honest.
from app.ml import pipeline_config as _canonical

__all__ = list(_canonical.__all__) + ["_find_project_root"]
