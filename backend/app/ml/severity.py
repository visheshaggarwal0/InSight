"""Single source of truth for complaint/theme severity classification.

Three divergent implementations previously shipped simultaneously
(``pipeline_config.SEVERITY`` consumers, ``real_loader``, ``clustering``),
producing different verdicts for identical inputs. All callers now route
through :func:`classify_severity`.
"""

from __future__ import annotations

from typing import Dict

from app.ml.pipeline_config import SEVERITY


def classify_severity(
    negative_fraction: float,
    volume: int,
    baseline_negative_fraction: float | None = None,
) -> str:
    """
    Classify a cluster into LOW / MEDIUM / HIGH / CRITICAL.

    Args:
        negative_fraction: share of the cluster predicted NEGATIVE, in [0, 1].
        volume: number of reviews in the cluster.
        baseline_negative_fraction: corpus-wide NEGATIVE share. When supplied,
            severity also accounts for how far a cluster *elevates* the corpus
            negative rate. Without it only the absolute thresholds apply.

    Rationale:
        The original ``high_neg_fraction`` was identical to
        ``critical_neg_fraction`` (0.35), so CRITICAL vs HIGH depended purely
        on the volume gate and HIGH was unreachable for large clusters.

        Absolute thresholds alone are also uninformative on a corpus whose
        overall negative rate is far below 0.35 (the Sephora corpus is ~12%):
        every cluster collapsed to LOW. The lift rules below restore signal
        without inventing it - a cluster is only escalated when it is both
        meaningfully elevated AND large enough for the estimate to hold.
    """
    frac = max(0.0, min(1.0, float(negative_fraction)))

    # Absolute rules (unchanged operating points).
    if frac >= SEVERITY["critical_neg_fraction"] and volume >= SEVERITY["critical_min_volume"]:
        return "CRITICAL"
    if frac >= SEVERITY["high_neg_fraction"]:
        return "HIGH"
    if frac >= SEVERITY["medium_neg_fraction"]:
        return "MEDIUM"

    # Relative rules: elevated versus this corpus's own baseline. These express
    # "unusually negative for THIS product", which is the only meaningful
    # signal on a corpus whose absolute negative rate never approaches 0.35.
    if baseline_negative_fraction and baseline_negative_fraction > 0 and volume >= 25:
        lift = frac / baseline_negative_fraction
        if lift >= 3.0 and frac >= 0.10 and volume >= 100:
            return "HIGH"
        if lift >= 2.0 and volume >= 50:
            return "MEDIUM"
        # >=25% more negative than the corpus average is worth surfacing.
        if lift >= 1.25:
            return "MEDIUM"

    return "LOW"


def corpus_negative_fraction(reviews) -> float:
    """Corpus-wide NEGATIVE share, used as the severity baseline."""
    if not reviews:
        return 0.0
    negative = sum(1 for r in reviews if r.get("sentiment_pred") == "NEGATIVE")
    return negative / len(reviews)


def classify_complaint_severity(count: int, total_complaints: int = 0) -> str:
    """
    Severity tier for a sentence-level complaint cluster.
    
    Uses relative percentage share of the total complaint pool:
      - Share >= 20.0% (and count >= 3) -> CRITICAL (P0)
      - Share >= 14.0% (and count >= 2) -> HIGH (P1)
      - Share >= 8.0%                   -> MEDIUM (P2)
      - Else                            -> LOW (P3)
      
    Falls back to absolute volume rules only when total_complaints is unknown.
    """
    if total_complaints and total_complaints > 0:
        share = count / total_complaints
        if share >= 0.20 and count >= 3:
            return "CRITICAL"
        if share >= 0.14 and count >= 2:
            return "HIGH"
        if share >= 0.08:
            return "MEDIUM"
        return "LOW"

    from app.ml.pipeline_config import COMPLAINT_CLUSTERING

    thresholds = COMPLAINT_CLUSTERING["severity_thresholds"]
    if count >= thresholds["critical"]:
        return "CRITICAL"
    if count >= thresholds["high"]:
        return "HIGH"
    if count >= thresholds["medium"]:
        return "MEDIUM"
    return "LOW"


def severity_snapshot() -> Dict[str, object]:
    """Expose the active thresholds so the dashboard never hardcodes them."""
    from app.ml.pipeline_config import COMPLAINT_CLUSTERING

    return {
        "theme": dict(SEVERITY),
        "complaint_cluster": dict(COMPLAINT_CLUSTERING["severity_thresholds"]),
    }
