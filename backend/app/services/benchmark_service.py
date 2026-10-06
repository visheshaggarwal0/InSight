import logging
from typing import Any, Dict, List, Optional
import math

logger = logging.getLogger(__name__)

class BenchmarkService:
    """
    Head-to-Head Comparative Intelligence Engine.
    Performs statistical delta analysis between release batches, product lots, or industry domains.
    """

    def compare_cohorts(
        self,
        reviews_a: List[Dict[str, Any]],
        reviews_b: List[Dict[str, Any]],
        label_a: str,
        label_b: str
    ) -> Dict[str, Any]:
        """
        Compares two cohorts (e.g. Batch 2021-Q3 vs 2021-Q4) side-by-side.
        """
        stats_a = self._compute_cohort_stats(reviews_a, label_a)
        stats_b = self._compute_cohort_stats(reviews_b, label_b)

        # Delta computations
        rating_delta = round(stats_b["avg_rating"] - stats_a["avg_rating"], 2)
        pos_delta = round(stats_b["positive_pct"] - stats_a["positive_pct"], 1)
        neg_delta = round(stats_b["negative_pct"] - stats_a["negative_pct"], 1)
        defect_rate_delta = round(stats_b["defect_rate_pct"] - stats_a["defect_rate_pct"], 1)

        # Divergent topic analysis
        theme_shifts = self._compute_topic_shifts(reviews_a, reviews_b)

        # Executive verdict
        if rating_delta <= -0.2 or neg_delta >= 4.0:
            verdict = f"REGRESSION: {label_b} shows noticeable degradation compared to {label_a}."
            verdict_badge = "CRITICAL_REGRESSION"
        elif rating_delta >= 0.2 or pos_delta >= 4.0:
            verdict = f"IMPROVEMENT: {label_b} outperforms {label_a} with higher customer satisfaction."
            verdict_badge = "SIGNIFICANT_IMPROVEMENT"
        else:
            verdict = f"STABLE: {label_b} displays parity with {label_a} within normal statistical bounds."
            verdict_badge = "STABLE_PARITY"

        return {
            "cohort_a": stats_a,
            "cohort_b": stats_b,
            "comparison": {
                "label_a": label_a,
                "label_b": label_b,
                "rating_delta": rating_delta,
                "positive_pct_delta": pos_delta,
                "negative_pct_delta": neg_delta,
                "defect_rate_delta": defect_rate_delta,
                "verdict": verdict,
                "verdict_badge": verdict_badge,
                "theme_shifts": theme_shifts,
                "win_loss_card": {
                    "winner": label_a if rating_delta < 0 else (label_b if rating_delta > 0 else "Tied"),
                    "key_advantage": (
                        f"Lower defect rate ({stats_a['defect_rate_pct']}% vs {stats_b['defect_rate_pct']}%)"
                        if stats_a['defect_rate_pct'] < stats_b['defect_rate_pct']
                        else f"Higher positive sentiment ({stats_b['positive_pct']}% vs {stats_a['positive_pct']}%)"
                    ),
                    "primary_headwind": (
                        f"Spike in '{theme_shifts[0]['theme']}' (+{theme_shifts[0]['rate_delta_pp']} pp)"
                        if theme_shifts and theme_shifts[0]["rate_delta_pp"] > 0
                        else "No severe headwind detected"
                    )
                }
            }
        }

    def _compute_cohort_stats(self, reviews: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
        n = max(len(reviews), 1)
        ratings = [r.get("rating") or 3 for r in reviews]
        avg_rating = round(sum(ratings) / n, 2)

        pos = sum(1 for r in reviews if (r.get("rating") or 3) >= 4)
        neg = sum(1 for r in reviews if (r.get("rating") or 3) <= 2)
        neu = len(reviews) - pos - neg

        # Sentence defect count
        defects = 0
        praise = 0
        for r in reviews:
            sents = r.get("sentences", [])
            if any(s.get("label") == "COMPLAINT" for s in sents) or (r.get("highlight_span") or {}).get("detected"):
                defects += 1
            if any(s.get("label") == "PRAISE" for s in sents):
                praise += 1

        # Rating distribution
        dist = {str(k): sum(1 for r in ratings if r == k) for k in range(1, 6)}

        return {
            "label": label,
            "total_reviews": len(reviews),
            "avg_rating": avg_rating,
            "positive_pct": round(pos / n * 100, 1),
            "neutral_pct": round(neu / n * 100, 1),
            "negative_pct": round(neg / n * 100, 1),
            "defect_count": defects,
            "defect_rate_pct": round(defects / n * 100, 1),
            "praise_count": praise,
            "praise_rate_pct": round(praise / n * 100, 1),
            "rating_distribution": dist
        }

    def _compute_topic_shifts(self, reviews_a: List[Dict[str, Any]], reviews_b: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        na = max(len(reviews_a), 1)
        nb = max(len(reviews_b), 1)

        def count_topics(revs):
            counts = {}
            for r in revs:
                t = r.get("theme_title") or "General"
                counts[t] = counts.get(t, 0) + 1
            return counts

        ca = count_topics(reviews_a)
        cb = count_topics(reviews_b)
        all_themes = sorted(set(list(ca.keys()) + list(cb.keys())))

        shifts = []
        for t in all_themes:
            c1 = ca.get(t, 0)
            c2 = cb.get(t, 0)
            r1 = (c1 / na) * 100
            r2 = (c2 / nb) * 100
            delta = round(r2 - r1, 1)
            rr = round((r2 / max(r1, 0.001)), 2)

            shifts.append({
                "theme": t,
                "cohort_a_count": c1,
                "cohort_b_count": c2,
                "cohort_a_pct": round(r1, 1),
                "cohort_b_pct": round(r2, 1),
                "rate_delta_pp": delta,
                "relative_risk": rr,
                "direction": "SURGE" if delta > 1.5 else ("DROP" if delta < -1.5 else "STABLE")
            })

        shifts.sort(key=lambda s: abs(s["rate_delta_pp"]), reverse=True)
        return shifts[:6]

benchmark_service = BenchmarkService()
