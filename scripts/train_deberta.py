"""scripts/train_deberta.py
Thin launcher for the single canonical DeBERTa training implementation.

The training logic lives in `InSight_ML/train_deberta.py`. This file previously
contained a byte-identical 311-line copy, so any fix (seeding, AMP, scheduler,
checkpointing, INT8 measurement) applied to one copy was silently absent from
the other.

Usage:
    python scripts/train_deberta.py --epochs 4 --batch-size 32
    python InSight_ML/train_deberta.py ...   # identical behaviour
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_ROOT), str(_ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from InSight_ML.train_deberta import main, train  # noqa: F401,E402

if __name__ == "__main__":
    sys.exit(main())
