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

    @staticmethod
    def compute_causal_attribution(
        baseline_dist: Dict[str, int],
        target_dist: Dict[str, int],
        baseline_total: int,
        target_total: int,
    ) -> List[Dict[str, Any]]:
        """
        Computes empirical Relative Risk (RR) and Fisher's exact test for each category/theme
        across baseline and target cohorts.

        Returns:
            List of causal attribution objects sorted by percentage point increase.
        """
        from scipy.stats import fisher_exact

        all_keys = list(set(baseline_dist.keys()).union(set(target_dist.keys())))
        b_total = max(int(baseline_total), 1)
        t_total = max(int(target_total), 1)
        drivers: List[Dict[str, Any]] = []

        for key in all_keys:
            k_base = int(baseline_dist.get(key, 0))
            k_target = int(target_dist.get(key, 0))

            p_base = k_base / b_total
            p_target = k_target / t_total
            delta_pp = (p_target - p_base) * 100.0

            # Haldane-Anscombe corrected Relative Risk (+0.5) to avoid division by 0
            rr = ((k_target + 0.5) / (t_total + 0.5)) / ((k_base + 0.5) / (b_total + 0.5))

            # 2x2 contingency table for Fisher's Exact Test:
            # [[Target_Key, Target_Other], [Baseline_Key, Baseline_Other]]
            contingency_table = [
                [k_target, max(0, t_total - k_target)],
                [k_base, max(0, b_total - k_base)],
            ]

            try:
                _, p_greater = fisher_exact(contingency_table, alternative="greater")
                _, p_two_sided = fisher_exact(contingency_table, alternative="two-sided")
                if np.isnan(p_greater):
                    p_greater = 1.0
                if np.isnan(p_two_sided):
                    p_two_sided = 1.0
            except Exception:
                p_greater = 1.0
                p_two_sided = 1.0

            is_sig = bool(p_greater < 0.05 and k_target >= 3 and delta_pp > 0)

            drivers.append({
                "theme": key,
                "target_count": k_target,
                "baseline_count": k_base,
                "target_rate_pct": round(p_target * 100.0, 2),
                "baseline_rate_pct": round(p_base * 100.0, 2),
                "rate_delta_pp": round(delta_pp, 2),
                "relative_risk": round(float(rr), 2),
                "p_value": round(float(p_greater), 5),
                "p_value_two_sided": round(float(p_two_sided), 5),
                "is_statistically_significant": is_sig,
                "significance_tier": (
                    "p < 0.001" if p_greater < 0.001
                    else ("p < 0.05" if p_greater < 0.05 else "n.s.")
                ),
            })

        # Sort primarily by rate_delta_pp descending, then by smallest p_value
        drivers.sort(key=lambda d: (d["rate_delta_pp"], -d["p_value"]), reverse=True)
        return drivers

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
        prev_total = 0

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
            surging_delta = 0.0
            drivers: List[Dict[str, Any]] = []

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

                drivers = self.compute_causal_attribution(
                    prev_theme_dist, theme_dist, prev_total, total
                )
                if drivers:
                    top_driver = drivers[0]
                    surging_theme = top_driver["theme"]
                    surging_delta = top_driver["rate_delta_pp"] / 100.0
                    relative_risk = top_driver["relative_risk"]
                    p_val = top_driver["p_value"]
                    is_sig = top_driver["is_statistically_significant"]
                else:
                    surging_theme = "Unknown"
                    surging_delta = 0.0
                    relative_risk = 1.0
                    p_val = 1.0
                    is_sig = False

                if psi >= critical:
                    drift_status = "CRITICAL_DRIFT"
                    alerts.append({
                        "severity": "CRITICAL",
                        "batch_or_version": b,
                        "psi_score": round(psi, 3),
                        "surging_theme": surging_theme,
                        "surging_theme_delta": round(surging_delta, 4),
                        "relative_risk": relative_risk,
                        "p_value": p_val,
                        "is_statistically_significant": is_sig,
                        "causal_drivers": drivers[:3],
                        "review_count": total,
                        "message": (
                            f"Critical distribution drift detected in {b} (PSI: {round(psi, 2)}). "
                            f"Largest increase: '{surging_theme}' (+{surging_delta * 100:.1f} pp, RR: {relative_risk}x, p={p_val:.4f})."
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
                        "relative_risk": relative_risk,
                        "p_value": p_val,
                        "is_statistically_significant": is_sig,
                        "causal_drivers": drivers[:3],
                        "review_count": total,
                        "message": (
                            f"Moderate topic drift detected in {b} (PSI: {round(psi, 2)}). "
                            f"Largest increase: '{surging_theme}' (+{surging_delta * 100:.1f} pp, RR: {relative_risk}x, p={p_val:.4f})."
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
                "causal_attribution": drivers[:5] if (i > 0 and drivers) else None,
            })

            prev_theme_dist = theme_dist
            prev_total = total

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
