"""scripts/validate_complaint_extraction.py
Offline validation report for complaint span extraction on the real cosmetics dataset.

Produces a markdown report at docs/reports/complaint_extraction_validation.md.

Usage (from project root):
    python scripts/validate_complaint_extraction.py

IMPORTANT: Detection rates reported here have no precision/recall interpretation
without manually labelled complaint spans. They are operational coverage metrics only.
"""

from __future__ import annotations
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_BACKEND = _ROOT / "backend"
for p in [str(_ROOT), str(_BACKEND)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
from app.ml.complaint_extraction import extract_complaint_span
from app.ml.pipeline_config import DATASETS

REPORT_PATH = _ROOT / "docs" / "reports" / "complaint_extraction_validation.md"
N_REVIEWS = 1000  # sample size for this validation report
SAMPLE_SEED = 42   # fixed so the sampled subset is reproducible across runs


def main():
    csv_path = DATASETS["cosmetics_10k"]
    if not csv_path.exists():
        print(f"ERROR: Dataset not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(csv_path)
    pool = df["review_text"].dropna().astype(str)
    n_sample = min(N_REVIEWS, len(pool))
    reviews = pool.sample(n=n_sample, random_state=SAMPLE_SEED).tolist()

    n_detected = 0
    examples = []

    for rev in reviews:
        result = extract_complaint_span(rev)
        detected = result["detected"]
        if detected:
            n_detected += 1
            txt, s, e = result["text"], result["start"], result["end"]
            if len(examples) < 5:
                examples.append((rev, txt, s, e))

    detection_rate = n_detected / max(len(reviews), 1) * 100

    lines = [
        "# Complaint Extraction Validation",
        "",
        f"**Dataset**: `{csv_path.name}` (seeded random sample of {N_REVIEWS} reviews, seed={SAMPLE_SEED} — real Sephora cosmetics data)",
        "",
        f"- Reviews processed: {len(reviews)}",
        f"- Detections: {n_detected} ({detection_rate:.1f}%)",
        f"- No complaint extracted: {len(reviews) - n_detected} ({100 - detection_rate:.1f}%)",
        "",
        "> **IMPORTANT**: Detection rate is a coverage metric only. Without manually",
        "> labelled complaint spans there is no ground truth for precision or recall.",
        "> A high detection rate may indicate false positives (e.g., 'but' in non-complaint",
        "> contexts). Treat this as provisional engineering output.",
        "",
        "## Representative Extracted Complaints",
        "",
    ]

    for rev, txt, s, e in examples:
        snippet = rev[:120].replace("\n", " ")
        lines.append(f"- **Review snippet**: `{snippet}...`")
        lines.append(f"  **Extracted span**: `{txt}` (offset {s}–{e})")
        lines.append("")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
