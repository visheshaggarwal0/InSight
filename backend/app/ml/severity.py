"""Single source of truth for complaint/theme severity classification.

Three divergent implementations previously shipped simultaneously
(``pipeline_config.SEVERITY`` consumers, ``real_loader``, ``clustering``),
producing different verdicts for identical inputs. All callers now route
through :func:`classify_severity`.
"""

from __future__ import annotations

from typing import Dict

from app.ml.pipeline_config import SEVERITY


_SEV_RANK: Dict[str, int] = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}


def classify_severity(
    negative_fraction: float,
    volume: int,
    baseline_negative_fraction: float | None = None,
    max_proposition_severity: str | None = None,
    p0_count: int = 0,
    p1_count: int = 0,
) -> str:
    """
    Classify a cluster into LOW / MEDIUM / HIGH / CRITICAL.

    Args:
        negative_fraction: share of the cluster predicted NEGATIVE, in [0, 1].
        volume: number of reviews in the cluster.
        baseline_negative_fraction: corpus-wide NEGATIVE share. When supplied,
            severity also accounts for how far a cluster *elevates* the corpus
            negative rate. Without it only the absolute thresholds apply.
        max_proposition_severity: highest proposition severity tier present in
            cluster ("P0", "P1", "P2", "P3").
        p0_count: number of P0 (severe defect / chemical burn / crash / safety)
            propositions within the cluster.
        p1_count: number of P1 (functional blocker / pump broken / data loss)
            propositions within the cluster.

    Rationale:
        The original ``high_neg_fraction`` was identical to
        ``critical_neg_fraction`` (0.35), so CRITICAL vs HIGH depended purely
        on the volume gate and HIGH was unreachable for large clusters.

        Absolute thresholds alone are also uninformative on a corpus whose
        overall negative rate is far below 0.35 (the Sephora corpus is ~12%):
        every cluster collapsed to LOW. The lift rules below restore signal
        without inventing it - a cluster is only escalated when it is both
        meaningfully elevated AND large enough for the estimate to hold.

        Proposition-conditioned escalation prevents the 'Trojan Horse' defect
        blindspot: clusters harboring verified P0 harm/safety or P1 blocker
        clauses are escalated monotonically.
    """
    frac = max(0.0, min(1.0, float(negative_fraction)))
    severity = "LOW"

    # Absolute rules (unchanged operating points).
    if frac >= SEVERITY["critical_neg_fraction"] and volume >= SEVERITY["critical_min_volume"]:
        severity = "CRITICAL"
    elif frac >= SEVERITY["high_neg_fraction"]:
        severity = "HIGH"
    elif frac >= SEVERITY["medium_neg_fraction"]:
        severity = "MEDIUM"

    # Relative rules: elevated versus this corpus's own baseline. These express
    # "unusually negative for THIS product", which is the only meaningful
    # signal on a corpus whose absolute negative rate never approaches 0.35.
    if baseline_negative_fraction and baseline_negative_fraction > 0 and volume >= 25:
        lift = frac / baseline_negative_fraction
        if lift >= 3.0 and frac >= 0.10 and volume >= 100:
            if _SEV_RANK["HIGH"] > _SEV_RANK[severity]:
                severity = "HIGH"
        elif lift >= 2.0 and volume >= 50:
            if _SEV_RANK["MEDIUM"] > _SEV_RANK[severity]:
                severity = "MEDIUM"
        # >=25% more negative than the corpus average is worth surfacing.
        elif lift >= 1.25:
            if _SEV_RANK["MEDIUM"] > _SEV_RANK[severity]:
                severity = "MEDIUM"

    # Proposition-conditioned escalation
    norm_max = (max_proposition_severity or "").strip().upper()
    has_p0 = p0_count > 0 or norm_max == "P0"
    has_p1 = p1_count > 0 or norm_max == "P1"

    if has_p0:
        if p0_count >= 3 or (p0_count >= 1 and (frac >= 0.10 or volume >= 25)):
            severity = "CRITICAL"
        elif _SEV_RANK["HIGH"] > _SEV_RANK[severity]:
            severity = "HIGH"
    elif has_p1:
        if p1_count >= 5 or (p1_count >= 2 and (frac >= 0.15 or volume >= 50)):
            if _SEV_RANK["HIGH"] > _SEV_RANK[severity]:
                severity = "HIGH"
        elif _SEV_RANK["MEDIUM"] > _SEV_RANK[severity]:
            severity = "MEDIUM"

    return severity


def corpus_negative_fraction(reviews) -> float:
    """Corpus-wide NEGATIVE share, used as the severity baseline."""
    if not reviews:
        return 0.0
    negative = sum(1 for r in reviews if r.get("sentiment_pred") == "NEGATIVE")
    return negative / len(reviews)


def classify_complaint_severity(
    count: int,
    total_complaints: int = 0,
    max_proposition_severity: str | None = None,
    p0_count: int = 0,
    p1_count: int = 0,
) -> str:
    """
    Severity tier for a sentence-level complaint cluster.
    
    Uses relative percentage share of the total complaint pool, with
    proposition-conditioned escalation for high-consequence P0/P1 defects:
      - Share >= 20.0% (and count >= 3) -> CRITICAL (P0)
      - Share >= 14.0% (and count >= 2) -> HIGH (P1)
      - Share >= 8.0%                   -> MEDIUM (P2)
      - Else                            -> LOW (P3)
      
    Falls back to absolute volume rules only when total_complaints is unknown.
    """
    severity = "LOW"
    if total_complaints and total_complaints > 0:
        share = count / total_complaints
        if share >= 0.20 and count >= 3:
            severity = "CRITICAL"
        elif share >= 0.14 and count >= 2:
            severity = "HIGH"
        elif share >= 0.08:
            severity = "MEDIUM"
        else:
            severity = "LOW"
    else:
        from app.ml.pipeline_config import COMPLAINT_CLUSTERING

        thresholds = COMPLAINT_CLUSTERING["severity_thresholds"]
        if count >= thresholds["critical"]:
            severity = "CRITICAL"
        elif count >= thresholds["high"]:
            severity = "HIGH"
        elif count >= thresholds["medium"]:
            severity = "MEDIUM"
        else:
            severity = "LOW"

    # Proposition-conditioned escalation
    norm_max = (max_proposition_severity or "").strip().upper()
    has_p0 = p0_count > 0 or norm_max == "P0"
    has_p1 = p1_count > 0 or norm_max == "P1"

    if has_p0:
        if p0_count >= 2 or (p0_count >= 1 and count >= 4):
            severity = "CRITICAL"
        elif _SEV_RANK["HIGH"] > _SEV_RANK[severity]:
            severity = "HIGH"
    elif has_p1:
        if p1_count >= 3 or (p1_count >= 1 and count >= 5):
            if _SEV_RANK["HIGH"] > _SEV_RANK[severity]:
                severity = "HIGH"
        elif _SEV_RANK["MEDIUM"] > _SEV_RANK[severity]:
            severity = "MEDIUM"

    return severity


def severity_snapshot() -> Dict[str, object]:
    """Expose the active thresholds so the dashboard never hardcodes them."""
    from app.ml.pipeline_config import COMPLAINT_CLUSTERING

    return {
        "theme": dict(SEVERITY),
        "complaint_cluster": dict(COMPLAINT_CLUSTERING["severity_thresholds"]),
    }
