import os
import sys
import time
import zipfile
import unittest
import numpy as np
import pandas as pd

# Add project root and InSight_ML to sys.path
ml_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(ml_dir, ".."))
for p in [ml_dir, root_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from InSight_ML.theme_inference import ThemeInferenceEngine, get_theme_engine

class TestThemeInferenceEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        t0 = time.time()
        cls.engine = get_theme_engine()
        cls.init_time = time.time() - t0
        print(f"\n[Test Setup] Engine initialized in {cls.init_time:.2f}s (Model load time: {cls.engine.model_load_time_sec}s)")

        # Load 10k dataset (Known Embedding Set)
        data_path = os.path.join(root_dir, "InSight_ML", "data", "processed", "cosmetics", "cosmetics_10k.csv")
        cls.df_10k = pd.read_csv(data_path)

        # Load offline cluster assignments for comparison
        assign_path = os.path.join(root_dir, "InSight_ML", "outputs", "theme_detection", "cluster_assignments.csv")
        cls.df_assign = pd.read_csv(assign_path) if os.path.exists(assign_path) else None

        # Extract 30 genuinely unseen reviews from archive.zip
        cls.unseen_reviews = []
        archive_path = os.path.join(root_dir, "InSight_ML", "data", "raw", "cosmetics", "archive.zip")
        if os.path.exists(archive_path):
            known_texts = set(cls.df_10k["review_text"].dropna().astype(str).tolist())
            with zipfile.ZipFile(archive_path, "r") as z:
                with z.open("reviews_1250-end.csv") as f:
                    df_arch = pd.read_csv(f, nrows=300)
                    df_arch = df_arch.dropna(subset=["review_text"])
                    filtered = df_arch[~df_arch["review_text"].isin(known_texts)]
                    cls.unseen_reviews = filtered["review_text"].head(30).tolist()

    def test_01_centroids_integrity_and_shape(self):
        """Verify that precomputed centroids have exact (6, 384) shape and unit norms."""
        self.assertEqual(self.engine.centroids.shape, (6, 384))
        norms = np.linalg.norm(self.engine.centroids, axis=1)
        np.testing.assert_allclose(norms, np.ones(6), atol=1e-5)
        self.assertEqual(len(self.engine.theme_names), 6)

    def test_02_single_review_inference_structure(self):
        """Verify single review prediction returns required keys, valid ranges, and provisional notice."""
        sample_text = "This moisturizer is deeply hydrating and restored my damaged skin barrier."
        res = self.engine.predict_theme(sample_text)

        required_keys = [
            "predicted_cluster_id", "provisional_theme", "cosine_similarity",
            "cluster_similarities", "cluster_similarity_by_theme",
            "is_provisional", "provisional_notice"
        ]
        for k in required_keys:
            self.assertIn(k, res, f"Missing key in prediction: {k}")

        self.assertIn(res["predicted_cluster_id"], range(6))
        self.assertIsInstance(res["provisional_theme"], str)
        self.assertTrue(np.isfinite(res["cosine_similarity"]))
        self.assertTrue(-1.0 <= res["cosine_similarity"] <= 1.0)
        self.assertTrue(res["is_provisional"])
        self.assertEqual(len(res["cluster_similarities"]), 6)

    def test_03_inference_on_30_known_reviews(self):
        """
        Validate inference on 30 reviews from the original 10,000-review embedding set.
        Measures latency, checks output validity, and compares to original offline assignments.
        """
        sample_30 = self.df_10k.sample(n=30, random_state=42)
        sample_indices = sample_30.index.tolist()
        sample_texts = sample_30["review_text"].tolist()

        t0 = time.time()
        predictions = self.engine.predict_themes_batch(sample_texts)
        batch_duration = time.time() - t0
        per_review_latency_ms = (batch_duration / len(sample_texts)) * 1000

        print(f"\n[Validation: 30 Known Reviews] Encoded in {batch_duration:.3f}s ({per_review_latency_ms:.2f} ms/review)")

        assigned_clusters = [p["predicted_cluster_id"] for p in predictions]
        cluster_counts = pd.Series(assigned_clusters).value_counts().to_dict()
        print(f"  Cluster distribution (Known 30): {cluster_counts}")

        # Check alignment against original cluster_assignments.csv if available
        if self.df_assign is not None:
            matches = 0
            for idx, pred in zip(sample_indices, predictions):
                orig_cid = int(self.df_assign.loc[idx, "minilm_cluster_k6"])
                if pred["predicted_cluster_id"] == orig_cid:
                    matches += 1
            concordance = matches / len(sample_indices)
            print(f"  Centroid proximity concordance with original KMeans: {concordance:.1%} ({matches}/30)")
            # Centroid nearest should match original KMeans assignments for high majority
            self.assertGreater(concordance, 0.70, "Centroid argmax should match original KMeans assignment on majority")

        self.assertEqual(len(predictions), 30)
        for p in predictions:
            self.assertIn(p["predicted_cluster_id"], range(6))
            self.assertTrue(-1.0 <= p["cosine_similarity"] <= 1.0)

    def test_04_inference_on_30_genuinely_unseen_reviews(self):
        """
        Validate inference on 30 genuinely unseen reviews from archive.zip (not in cosmetics_10k.csv).
        Verifies behavior on novel text without data contamination.
        """
        if not self.unseen_reviews:
            self.skipTest("Unseen reviews from archive.zip not available.")

        self.assertEqual(len(self.unseen_reviews), 30)
        
        t0 = time.time()
        predictions = self.engine.predict_themes_batch(self.unseen_reviews)
        batch_duration = time.time() - t0
        per_review_latency_ms = (batch_duration / len(self.unseen_reviews)) * 1000

        print(f"\n[Validation: 30 Genuinely Unseen Reviews] Encoded in {batch_duration:.3f}s ({per_review_latency_ms:.2f} ms/review)")

        assigned_clusters = [p["predicted_cluster_id"] for p in predictions]
        cluster_counts = pd.Series(assigned_clusters).value_counts().to_dict()
        print(f"  Cluster distribution (Unseen 30): {cluster_counts}")

        for p in predictions:
            self.assertIn(p["predicted_cluster_id"], range(6))
            self.assertTrue(np.isfinite(p["cosine_similarity"]))
            self.assertTrue(p["is_provisional"])
            # All 6 cluster similarities must be present
            self.assertEqual(len(p["cluster_similarities"]), 6)

    def test_05_determinism_and_batch_consistency(self):
        """Verify deterministic predictions and equivalence between single and batch inference."""
        sample_texts = [
            "Great eye cream for dark circles and puffiness.",
            "Smells like fresh citrus, very refreshing face mist.",
            "Helps clear my acne and blemishes with salicylic acid."
        ]

        single_preds = [self.engine.predict_theme(t) for t in sample_texts]
        batch_preds = self.engine.predict_themes_batch(sample_texts)

        for s, b in zip(single_preds, batch_preds):
            self.assertEqual(s["predicted_cluster_id"], b["predicted_cluster_id"])
            self.assertEqual(s["provisional_theme"], b["provisional_theme"])
            self.assertAlmostEqual(s["cosine_similarity"], b["cosine_similarity"], places=4)

    def test_06_blank_and_invalid_inputs(self):
        """Verify robust handling of empty strings and whitespace."""
        res_empty = self.engine.predict_theme("")
        self.assertEqual(res_empty["predicted_cluster_id"], -1)
        self.assertEqual(res_empty["cosine_similarity"], 0.0)

        res_space = self.engine.predict_theme("   \n\t  ")
        self.assertEqual(res_space["predicted_cluster_id"], -1)

if __name__ == "__main__":
    unittest.main()
