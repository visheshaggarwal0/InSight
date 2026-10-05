"""test_drift_causal_attribution.py
Tests for Causal Attribution and Statistical Significance (Fisher's exact test, Relative Risk)
in TemporalDriftDetector.
"""

import unittest
from app.ml.drift import TemporalDriftDetector


class TestDriftCausalAttribution(unittest.TestCase):

    def test_causal_attribution_statistically_significant_surge(self):
        detector = TemporalDriftDetector()
        baseline_dist = {"Moisturizers": 500, "Cleansers": 490, "Defective Pump": 10}
        target_dist = {"Moisturizers": 450, "Cleansers": 450, "Defective Pump": 100}
        baseline_total = 1000
        target_total = 1000

        drivers = detector.compute_causal_attribution(
            baseline_dist, target_dist, baseline_total, target_total
        )

        self.assertGreater(len(drivers), 0)
        top_driver = drivers[0]
        self.assertEqual(top_driver["theme"], "Defective Pump")
        self.assertGreater(top_driver["relative_risk"], 5.0)
        self.assertLess(top_driver["p_value"], 0.001)
        self.assertTrue(top_driver["is_statistically_significant"])
        self.assertEqual(top_driver["significance_tier"], "p < 0.001")

    def test_causal_attribution_stable_cohort(self):
        detector = TemporalDriftDetector()
        baseline_dist = {"Moisturizers": 500, "Cleansers": 500}
        target_dist = {"Moisturizers": 505, "Cleansers": 495}
        baseline_total = 1000
        target_total = 1000

        drivers = detector.compute_causal_attribution(
            baseline_dist, target_dist, baseline_total, target_total
        )

        for d in drivers:
            self.assertFalse(d["is_statistically_significant"])
            self.assertAlmostEqual(d["relative_risk"], 1.0, delta=0.2)

    def test_causal_attribution_zero_counts_edge_case(self):
        detector = TemporalDriftDetector()
        baseline_dist = {"New Defect": 0}
        target_dist = {"New Defect": 0}

        drivers = detector.compute_causal_attribution(
            baseline_dist, target_dist, baseline_total=100, target_total=100
        )
        self.assertEqual(len(drivers), 1)
        self.assertEqual(drivers[0]["p_value"], 1.0)
        self.assertFalse(drivers[0]["is_statistically_significant"])

    def test_analyze_drift_timeline_includes_causal_attribution(self):
        detector = TemporalDriftDetector()
        reviews = []
        # Batch-1: baseline (200 reviews)
        for i in range(200):
            reviews.append({
                "batch_or_version": "Batch-1",
                "theme_title": "Packaging" if i < 10 else "General Quality",
                "sentiment_pred": "POSITIVE",
            })
        # Batch-2: sudden surge in Packaging (100 out of 200)
        for i in range(200):
            reviews.append({
                "batch_or_version": "Batch-2",
                "theme_title": "Packaging" if i < 100 else "General Quality",
                "sentiment_pred": "NEGATIVE" if i < 100 else "POSITIVE",
            })

        res = detector.analyze_drift(reviews)
        self.assertIn("timeline", res)
        self.assertEqual(len(res["timeline"]), 2)

        batch_2_entry = res["timeline"][1]
        self.assertIsNotNone(batch_2_entry["causal_attribution"])
        self.assertGreater(len(batch_2_entry["causal_attribution"]), 0)
        top_cause = batch_2_entry["causal_attribution"][0]
        self.assertEqual(top_cause["theme"], "Packaging")
        self.assertTrue(top_cause["is_statistically_significant"])

        # Check alert causal fields
        self.assertGreater(len(res["alerts"]), 0)
        alert = res["alerts"][0]
        self.assertIn("causal_drivers", alert)
        self.assertIn("relative_risk", alert)
        self.assertIn("p_value", alert)
        self.assertEqual(alert["surging_theme"], "Packaging")
        self.assertTrue(alert["is_statistically_significant"])


if __name__ == "__main__":
    unittest.main()
