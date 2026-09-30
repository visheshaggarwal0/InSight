"""scripts/run_pipeline.py
Thin launcher for the single canonical pipeline implementation.

The pipeline logic lives in `InSight_ML/run_pipeline.py`. This file previously
contained a byte-identical 676-line copy of that module, so any fix applied to
one copy was silently absent from the other, and the two copies imported
different *physical* copies of `pipeline_config`.

Usage:
    python scripts/run_pipeline.py [--dataset cosmetics_10k] [--output-dir ...]
    python InSight_ML/run_pipeline.py  ...   # identical behaviour
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_ROOT), str(_ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from InSight_ML.run_pipeline import main, run_pipeline  # noqa: F401,E402

if __name__ == "__main__":
    sys.exit(main())
