import numpy as np
from typing import List, Dict, Any

class TemporalDriftDetector:
    """
    Detects statistical distribution drift and regressions across product batches
    (e.g., Batch-24A vs Batch-24C) or software releases (v2.1 vs v2.4).
    Calculates Population Stability Index (PSI).
    """

    @staticmethod
    def calculate_psi(baseline_dist: Dict[str, int], target_dist: Dict[str, int], epsilon: float = 1e-4) -> float:
        """
        Calculates Population Stability Index (PSI) between two categorical distributions.
        PSI = sum((Target_i - Baseline_i) * ln(Target_i / Baseline_i))
        """
        all_keys = list(set(baseline_dist.keys()).union(set(target_dist.keys())))
        
        base_total = sum(baseline_dist.values()) or 1
        target_total = sum(target_dist.values()) or 1

        psi_val = 0.0
        for k in all_keys:
            base_p = (baseline_dist.get(k, 0) / base_total) + epsilon
            target_p = (target_dist.get(k, 0) / target_total) + epsilon
            
            psi_val += (target_p - base_p) * np.log(target_p / base_p)

        return float(psi_val)

    def analyze_drift(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Groups reviews by batch_or_version chronologically,
        computes release-over-release PSI, and checks for regression alerts.
        """
        # Collect distinct versions / batches
        batch_order = []
        batch_groups: Dict[str, List[Dict[str, Any]]] = {}

        for r in reviews:
            b = r.get("batch_or_version", "Batch-1")
            if b not in batch_groups:
                batch_order.append(b)
                batch_groups[b] = []
            batch_groups[b].append(r)

        timeline = []
        alerts = []

        for i, b in enumerate(batch_order):
            items = batch_groups[b]
            total = len(items)
            neg_count = sum(1 for x in items if x.get("sentiment_pred") == "NEGATIVE")
            pos_count = sum(1 for x in items if x.get("sentiment_pred") == "POSITIVE")
            neu_count = sum(1 for x in items if x.get("sentiment_pred") == "NEUTRAL")

            theme_dist: Dict[str, int] = {}
            for x in items:
                t = x.get("theme_title", "General")
                theme_dist[t] = theme_dist.get(t, 0) + 1

            neg_rate = round((neg_count / total * 100), 1) if total > 0 else 0.0

            # Calculate PSI compared to prior batch/release
            psi = 0.0
            drift_status = "STABLE"

            if i > 0:
                prev_b = batch_order[i - 1]
                prev_items = batch_groups[prev_b]
                prev_theme_dist: Dict[str, int] = {}
                for x in prev_items:
                    t = x.get("theme_title", "General")
                    prev_theme_dist[t] = prev_theme_dist.get(t, 0) + 1

                psi = self.calculate_psi(prev_theme_dist, theme_dist)

                if psi >= 0.25:
                    drift_status = "CRITICAL_DRIFT"
                    # Find top surging complaint in this batch
                    surging_theme = max(theme_dist, key=theme_dist.get) if theme_dist else "Unknown"
                    alerts.append({
                        "severity": "CRITICAL",
                        "batch_or_version": b,
                        "psi_score": round(psi, 3),
                        "surging_theme": surging_theme,
                        "message": f"Critical distribution drift detected in {b} (PSI: {round(psi, 2)}). Severe surge in '{surging_theme}'."
                    })
                elif psi >= 0.10:
                    drift_status = "MODERATE_DRIFT"
                    alerts.append({
                        "severity": "WARNING",
                        "batch_or_version": b,
                        "psi_score": round(psi, 3),
                        "message": f"Moderate topic drift detected in {b} (PSI: {round(psi, 2)})."
                    })

            timeline.append({
                "batch_or_version": b,
                "review_count": total,
                "negative_count": neg_count,
                "neutral_count": neu_count,
                "positive_count": pos_count,
                "negative_rate": neg_rate,
                "psi": round(psi, 3),
                "status": drift_status,
                "themes": theme_dist
            })

        return {
            "timeline": timeline,
            "alerts": alerts,
            "batches_analyzed": len(batch_order)
        }

drift_detector = TemporalDriftDetector()
