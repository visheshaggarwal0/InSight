import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class ROIService:
    """
    Action & ROI Impact Matrix Service.
    Translates unstructured customer defect telemetry into prioritized engineering backlog
    with calculated CSAT lift and sprint effort estimations.
    """

    def compute_action_matrix(
        self,
        complaint_clusters: List[Dict[str, Any]],
        total_reviews: int,
        baseline_rating: float
    ) -> Dict[str, Any]:
        """
        Maps defect clusters into an impact vs. effort matrix with projected CSAT uplift.
        """
        total = max(total_reviews, 1)
        matrix_items = []

        # Complexity / Effort heuristics based on cluster title keywords
        def estimate_effort(title: str, severity: str) -> str:
            t_lower = title.lower()
            if any(k in t_lower for k in ["formula", "burn", "reaction", "ingredient", "architecture", "rewrite"]):
                return "HIGH" # Formulation redesign or architectural refactor
            if any(k in t_lower for k in ["packaging", "pump", "cap", "leak", "biometric", "button", "ui"]):
                return "MEDIUM" # Mechanical component or UI bugfix
            return "LOW" # Copy change, docs, minor tuning

        total_potential_lift = 0.0

        for i, c in enumerate(complaint_clusters):
            count = c.get("count", 1)
            severity = c.get("severity", "P2")
            title = c.get("title", f"Defect Cluster #{i+1}")
            blast_radius_pct = round(count / total * 100, 2)

            effort = estimate_effort(title, severity)

            # Impact Score (1-100) based on blast radius and severity weight
            sev_multiplier = {"P0": 3.0, "P1": 2.0, "P2": 1.2, "P3": 0.8}.get(severity, 1.0)
            impact_score = min(round((blast_radius_pct * 4.0) * sev_multiplier, 1), 99.0)

            # Projected CSAT Uplift (assumes resolving defect brings negative reviews to clean average 4.2★)
            # Delta = (count * (4.2 - 1.5)) / total
            csat_lift = round((count * 2.7) / total, 3)
            total_potential_lift += csat_lift

            # Assign Quadrant
            if impact_score >= 50 and effort in ["LOW", "MEDIUM"]:
                quadrant = "QUICK_WIN" # High Impact, Moderate Effort
                recommendation = "Immediate Sprint Target — High CSAT Uplift"
            elif severity == "P0" or (impact_score >= 60 and effort == "HIGH"):
                quadrant = "CRITICAL_BLOCKER" # Highest Urgency
                recommendation = "Immediate Quality Alert — Formulate Root Cause Fix"
            elif effort == "HIGH" and impact_score < 50:
                quadrant = "STRATEGIC_REVAMP" # Complex redesign
                recommendation = "Schedule for Next Quarterly Release Cycle"
            else:
                quadrant = "QUALITY_OF_LIFE" # Incremental polish
                recommendation = "Backlog Fill-in / Minor Polish"

            story_points = {"LOW": 3, "MEDIUM": 5, "HIGH": 13}.get(effort, 5)

            matrix_items.append({
                "id": c.get("cluster_id", i),
                "title": title,
                "severity": severity,
                "incident_count": count,
                "blast_radius_pct": blast_radius_pct,
                "impact_score": impact_score,
                "effort": effort,
                "story_points": story_points,
                "quadrant": quadrant,
                "projected_csat_lift": f"+{csat_lift:.2f}★",
                "csat_lift_val": csat_lift,
                "recommendation": recommendation,
                "estimated_retention_roi": f"${count * 45:,} / mo" # Est $45 churned LTV per defect
            })

        # Sort by impact score descending
        matrix_items.sort(key=lambda x: x["impact_score"], reverse=True)

        return {
            "baseline_csat": baseline_rating,
            "projected_target_csat": round(min(baseline_rating + min(total_potential_lift, 0.75), 5.0), 2),
            "max_potential_lift": f"+{min(total_potential_lift, 0.75):.2f}★",
            "items": matrix_items,
            "quadrant_counts": {
                "quick_wins": sum(1 for m in matrix_items if m["quadrant"] == "QUICK_WIN"),
                "critical_blockers": sum(1 for m in matrix_items if m["quadrant"] == "CRITICAL_BLOCKER"),
                "strategic_revamp": sum(1 for m in matrix_items if m["quadrant"] == "STRATEGIC_REVAMP"),
                "quality_of_life": sum(1 for m in matrix_items if m["quadrant"] == "QUALITY_OF_LIFE")
            }
        }

roi_service = ROIService()
