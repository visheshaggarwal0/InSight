import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.data.real_loader import real_data_loader, RealDataLoader

class TestRealDataLoader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = RealDataLoader()
        cls.data = cls.loader.load_data()
        cls.reviews = cls.data["reviews"]
        cls.themes = cls.data["themes"]
        cls.drift = cls.data["drift_results"]

    def test_01_dataset_loading_and_row_count(self):
        """Verify full 10,000 review loading without row loss or truncation."""
        self.assertEqual(len(self.reviews), 10000, "Review count should be exactly 10,000")
        self.assertEqual(self.data["row_count"], 10000)

    def test_02_stable_ids_and_artifact_joins(self):
        """Verify deterministic review IDs and consistent 1-to-1 artifact joining."""
        first_rev = self.reviews[0]
        self.assertEqual(first_rev["id"], "REV-SEP-00000")
        last_rev = self.reviews[-1]
        self.assertEqual(last_rev["id"], "REV-SEP-09999")
        
        # Verify IDs are unique across all 10,000 reviews
        all_ids = [r["id"] for r in self.reviews]
        self.assertEqual(len(set(all_ids)), 10000, "All review IDs must be strictly unique")

        # Verify cluster_id is within 0 to 5
        cluster_ids = {r["cluster_id"] for r in self.reviews}
        self.assertEqual(cluster_ids, {0, 1, 2, 3, 4, 5})

    def test_03_timestamp_and_quarterly_cohorts(self):
        """Verify valid quarterly cohort formatting (YYYY-Q#) and no synthetic batch strings."""
        cohorts = {r["batch_or_version"] for r in self.reviews}
        import re
        cohort_pattern = re.compile(r"^\d{4}-Q[1-4]$")
        for c in cohorts:
            self.assertTrue(cohort_pattern.match(c), f"Cohort '{c}' does not match 'YYYY-Q#' format")

        # Verify synthetic batch strings are completely absent
        for c in cohorts:
            self.assertNotIn("Batch-24", c)
            self.assertNotIn("Batch-", c)

    def test_04_no_synthetic_data_generation(self):
        """Verify reviews and brands originate from real Sephora dataset, not synthetic templates."""
        sample_brands = {r["brand_name"] for r in self.reviews[:100]}
        self.assertNotIn("Aura Botanicals", sample_brands, "Synthetic brand 'Aura Botanicals' must not exist")
        
        # Check presence of known real Sephora brands
        known_real_brands = {"Dr. Jart+", "Origins", "Murad", "IT Cosmetics"}
        self.assertTrue(len(known_real_brands.intersection(sample_brands)) > 0, "Expected real Sephora brands")

    def test_05_output_schema_compatibility(self):
        """Verify all review and theme dictionary keys match backend route expectations."""
        required_review_keys = [
            "id", "domain", "product_name", "brand_name", "product_id",
            "sku_or_module", "batch_or_version", "channel", "rating",
            "raw_text", "redacted_text", "pii_detected", "sentiment_pred",
            "sentiment_confidence", "cluster_id", "theme_title", "highlight_span"
        ]
        sample = self.reviews[0]
        for key in required_review_keys:
            self.assertIn(key, sample, f"Review missing required key: {key}")

        # Check sentiment values are standardized uppercase
        sentiments = {r["sentiment_pred"] for r in self.reviews}
        self.assertEqual(sentiments, {"POSITIVE", "NEUTRAL", "NEGATIVE"})

        # Check theme schema
        self.assertEqual(len(self.themes), 6, "Expected 6 theme clusters")
        required_theme_keys = [
            "cluster_id", "title", "keywords", "severity",
            "review_count", "sentiment_distribution", "negative_rate", "sample_verbatims"
        ]
        for t in self.themes:
            for key in required_theme_keys:
                self.assertIn(key, t, f"Theme missing required key: {key}")
            self.assertIn(t["severity"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])

    def test_06_drift_timeline_output(self):
        """Verify drift timeline structure and PSI calculation on real cohorts."""
        self.assertIn("timeline", self.drift)
        timeline = self.drift["timeline"]
        self.assertGreater(len(timeline), 0, "Timeline should contain chronological cohorts")
        
        first_entry = timeline[0]
        self.assertIn("batch_or_version", first_entry)
        self.assertIn("review_count", first_entry)
        self.assertIn("psi", first_entry)

    def test_07_theme_centroids_artifact(self):
        """Verify that theme_centroids.npy exists, has shape (6, 384), and unit norm."""
        centroids_path = os.path.join(
            self.loader.base_dir, "outputs", "theme_detection", "theme_centroids.npy"
        )
        self.assertTrue(os.path.exists(centroids_path), "theme_centroids.npy must exist")
        centroids = np.load(centroids_path)
        self.assertEqual(centroids.shape, (6, 384))
        norms = np.linalg.norm(centroids, axis=1)
        np.testing.assert_allclose(norms, np.ones(6), atol=1e-5)

    def test_08_error_handling_on_mismatched_row_counts(self):
        """Verify that load_data raises ValueError if an artifact has mismatched rows."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("row_index,minilm_cluster_k6,review_text\n0,1,Test\n")
            temp_path = f.name
        
        try:
            with self.assertRaises(ValueError):
                self.loader.load_data(cluster_assignments_path=temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    unittest.main()
