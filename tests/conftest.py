import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"

for p in [_ROOT, _BACKEND]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
