import logging
from typing import List, Dict, Any

import numpy as np

from app.ml.pipeline_config import PSI

logger = logging.getLogger(__name__)

# Cohorts smaller than this produce PSI estimates dominated by sampling noise.
# Real quarterly cohorts on a 10k corpus can be as small as ~11 reviews, where
# PSI is meaningless and alerting guarantees fatigue. Such cohorts are reported
# as INSUFFICIENT_DATA and never raise an alert.
MIN_COHORT_SIZE = 100


class TemporalDriftDetector:
    """
    Detects statistical distribution drift and regressions across product batches
    (e.g., Batch-24A vs Batch-24C) or software releases (v2.1 vs v2.4).
    Calculates Population Stability Index (PSI).

    Thresholds come from ``pipeline_config.PSI`` (single source of truth).
    """

    @staticmethod
    def calculate_psi(baseline_dist: Dict[str, int], target_dist: Dict[str, int], epsilon: float = 1e-4) -> float:
        """
        Calculates Population Stability Index (PSI) between two categorical distributions.

        PSI = sum((Target_i - Baseline_i) * ln(Target_i / Baseline_i))

        Raises:
            ValueError: if either distribution is empty, because PSI is
                undefined without a populated baseline.
        """
        if not baseline_dist or not target_dist:
            raise ValueError("PSI is undefined for an empty distribution.")

        all_keys = list(set(baseline_dist.keys()).union(set(target_dist.keys())))

        base_total = sum(baseline_dist.values())
        target_total = sum(target_dist.values())
        if base_total <= 0 or target_total <= 0:
            raise ValueError("PSI is undefined when a distribution has zero total count.")

        psi_val = 0.0
        for k in all_keys:
            base_p = (baseline_dist.get(k, 0) / base_total) + epsilon
            target_p = (target_dist.get(k, 0) / target_total) + epsilon
            psi_val += (target_p - base_p) * np.log(target_p / base_p)

        # PSI is a KL-style divergence: non-negative by construction, but the
        # epsilon floor can produce tiny negative values through float error.
        return float(max(psi_val, 0.0))

    def analyze_drift(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Groups reviews by batch_or_version, computes release-over-release PSI
        against the immediately preceding cohort, and raises regression alerts.

        Cohort ordering is a stable lexicographic sort of ``batch_or_version``.
        Callers that have a true chronological ordering (e.g. the pipeline,
        which pre-sorts by submission date) must pass pre-sorted reviews, or
        use :meth:`analyze_drift_ordered`.
        """
        batch_groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in reviews:
            batch_groups.setdefault(r.get("batch_or_version", "Batch-1"), []).append(r)

        # Deterministic cohort ordering.
        batch_order = sorted(batch_groups.keys())
        return self._build_timeline(batch_order, batch_groups)

    def analyze_drift_ordered(
        self, reviews: List[Dict[str, Any]], batch_order: List[str]
    ) -> Dict[str, Any]:
        """Variant that honours an explicit (e.g. chronological) cohort order."""
        batch_groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in reviews:
            batch_groups.setdefault(r.get("batch_or_version", "Batch-1"), []).append(r)
        return self._build_timeline(batch_order, batch_groups)

    def _theme_distribution(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for x in items:
            t = x.get("theme_title", "General")
            dist[t] = dist.get(t, 0) + 1
        return dist

    def _build_timeline(
        self,
        batch_order: List[str],
        batch_groups: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        moderate = PSI["moderate_threshold"]
        critical = PSI["critical_threshold"]

        timeline = []
        alerts = []
        prev_theme_dist: Dict[str, int] = {}

        for i, b in enumerate(batch_order):
            items = batch_groups[b]
            total = len(items)
            neg_count = sum(1 for x in items if x.get("sentiment_pred") == "NEGATIVE")
            pos_count = sum(1 for x in items if x.get("sentiment_pred") == "POSITIVE")
            neu_count = sum(1 for x in items if x.get("sentiment_pred") == "NEUTRAL")

            theme_dist = self._theme_distribution(items)
            neg_rate = round((neg_count / total * 100), 1) if total > 0 else 0.0

            psi: float | None = None
            drift_status = "BASELINE"
            surging_theme = None

            if i == 0:
                # First cohort is the reference period / baseline.
                drift_status = "BASELINE"
                psi = 0.0
            elif total < MIN_COHORT_SIZE or len(prev_theme_dist) == 0:
                drift_status = "INSUFFICIENT_DATA"
                logger.debug(
                    "Skipping PSI for cohort %s: %d reviews (min %d).",
                    b, total, MIN_COHORT_SIZE,
                )
            else:
                psi = self.calculate_psi(prev_theme_dist, theme_dist)

                # A "surge" is the largest INCREASE in share, not the largest
                # cluster. Picking max(count) named the dominant theme for every
                # alert in the timeline.
                surging_theme = max(
                    set(theme_dist) | set(prev_theme_dist),
                    key=lambda t: theme_dist.get(t, 0) - prev_theme_dist.get(t, 0),
                )
                surging_delta = (theme_dist.get(surging_theme, 0) - prev_theme_dist.get(surging_theme, 0)) / total

                if psi >= critical:
                    drift_status = "CRITICAL_DRIFT"
                    alerts.append({
                        "severity": "CRITICAL",
                        "batch_or_version": b,
                        "psi_score": round(psi, 3),
                        "surging_theme": surging_theme,
                        "surging_theme_delta": round(surging_delta, 4),
                        "review_count": total,
                        "message": (
                            f"Critical distribution drift detected in {b} (PSI: {round(psi, 2)}). "
                            f"Largest increase: '{surging_theme}' (+{surging_delta * 100:.1f} pp)."
                        ),
                    })
                elif psi >= moderate:
                    drift_status = "MODERATE_DRIFT"
                    alerts.append({
                        "severity": "WARNING",
                        "batch_or_version": b,
                        "psi_score": round(psi, 3),
                        "surging_theme": surging_theme,
                        "surging_theme_delta": round(surging_delta, 4),
                        "review_count": total,
                        "message": (
                            f"Moderate topic drift detected in {b} (PSI: {round(psi, 2)}). "
                            f"Largest increase: '{surging_theme}' (+{surging_delta * 100:.1f} pp)."
                        ),
                    })
                else:
                    drift_status = "STABLE"

            timeline.append({
                "batch_or_version": b,
                "review_count": total,
                "negative_count": neg_count,
                "neutral_count": neu_count,
                "positive_count": pos_count,
                "negative_rate": neg_rate,
                "psi": round(psi, 3) if psi is not None else None,
                "status": drift_status,
                "sufficient_data": total >= MIN_COHORT_SIZE,
                "themes": theme_dist,
            })

            prev_theme_dist = theme_dist

        return {
            "timeline": timeline,
            "alerts": alerts,
            "batches_analyzed": len(batch_order),
            "min_cohort_size": MIN_COHORT_SIZE,
            "thresholds": {"moderate": moderate, "critical": critical},
            "cohorts_skipped_for_small_n": sum(
                1 for t in timeline if t["status"] == "INSUFFICIENT_DATA"
            ),
        }


drift_detector = TemporalDriftDetector()
