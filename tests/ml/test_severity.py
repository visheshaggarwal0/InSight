"""test_severity.py
Unit tests for proposition-conditioned severity scoring in app.ml.severity.
"""

import unittest
from app.ml.severity import (
    classify_severity,
    classify_complaint_severity,
    corpus_negative_fraction,
    severity_snapshot,
)


class TestPropositionConditionedSeverity(unittest.TestCase):

    def test_standard_absolute_and_lift_thresholds(self):
        # Default low
        self.assertEqual(classify_severity(0.05, 50), "LOW")

        # Medium threshold (0.20)
        self.assertEqual(classify_severity(0.22, 50), "MEDIUM")

        # High threshold (0.35)
        self.assertEqual(classify_severity(0.36, 50), "HIGH")

        # Critical threshold (0.35 with volume >= 500)
        self.assertEqual(classify_severity(0.36, 600), "CRITICAL")

        # Relative baseline lift: corpus baseline 0.05, cluster 0.12 (lift 2.4, vol 60) -> MEDIUM
        self.assertEqual(classify_severity(0.12, 60, baseline_negative_fraction=0.05), "MEDIUM")

    def test_p0_proposition_escalation(self):
        # A cluster with low negative fraction (e.g. 5%) but containing a severe P0 defect (burn, crash)
        # Low volume (<25) with 1 P0 escalates to at least HIGH
        self.assertEqual(
            classify_severity(0.05, 20, max_proposition_severity="P0", p0_count=1),
            "HIGH"
        )

        # 1 P0 with volume >= 25 escalates to CRITICAL
        self.assertEqual(
            classify_severity(0.05, 30, max_proposition_severity="P0", p0_count=1),
            "CRITICAL"
        )

        # 3 or more P0s unconditionally escalates to CRITICAL regardless of low volume
        self.assertEqual(
            classify_severity(0.02, 10, max_proposition_severity="P0", p0_count=3),
            "CRITICAL"
        )

    def test_p1_proposition_escalation(self):
        # P1 functional failure (broken pump, freeze) escalates low cluster to MEDIUM
        self.assertEqual(
            classify_severity(0.05, 20, max_proposition_severity="P1", p1_count=1),
            "MEDIUM"
        )

        # Multiple P1s with elevated volume escalates to HIGH
        self.assertEqual(
            classify_severity(0.08, 60, max_proposition_severity="P1", p1_count=2),
            "HIGH"
        )

    def test_monotonic_severity_guarantee(self):
        # If absolute rules already classify as CRITICAL, P3/P2/P1 propositions do not downgrade it
        self.assertEqual(
            classify_severity(0.40, 600, max_proposition_severity="P3", p0_count=0),
            "CRITICAL"
        )

    def test_classify_complaint_severity_escalation(self):
        # Small volume cluster (count=2 out of 50 = 4% share, normally LOW)
        self.assertEqual(classify_complaint_severity(count=2, total_complaints=50), "LOW")

        # Escalated by P0
        self.assertEqual(
            classify_complaint_severity(count=2, total_complaints=50, max_proposition_severity="P0", p0_count=1),
            "HIGH"
        )

        # Escalated to CRITICAL with 2 P0s or count >= 4 with P0
        self.assertEqual(
            classify_complaint_severity(count=4, total_complaints=50, max_proposition_severity="P0", p0_count=1),
            "CRITICAL"
        )

    def test_corpus_negative_fraction_and_snapshot(self):
        reviews = [
            {"sentiment_pred": "POSITIVE"},
            {"sentiment_pred": "NEGATIVE"},
            {"sentiment_pred": "NEUTRAL"},
            {"sentiment_pred": "NEGATIVE"},
        ]
        self.assertAlmostEqual(corpus_negative_fraction(reviews), 0.5)

        snap = severity_snapshot()
        self.assertIn("theme", snap)
        self.assertIn("complaint_cluster", snap)


if __name__ == "__main__":
    unittest.main()
