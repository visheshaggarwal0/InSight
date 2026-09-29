"""test_pipeline_integration.py
Integration tests for the complete InSight ML pipeline.

Covers:
  - Complaint extraction: regex correctness, offset verification, edge cases
  - Validation module: schema checks, edge case handling
  - Sentiment pipeline: load, predict, distribution sanity
  - Theme assignment: alignment, cluster coverage
  - Drift detection: PSI calculation, timeline structure
  - End-to-end pipeline: full run on cosmetics dataset

Run from the project root:
    python -m pytest InSight_ML/tests/test_pipeline_integration.py -v

Or with unittest:
    python InSight_ML/tests/test_pipeline_integration.py
"""

from __future__ import annotations

import os
import sys
import time
import unittest
import tempfile
from pathlib import Path
from collections import Counter
from typing import List, Dict

import numpy as np
import pandas as pd

# ── Path setup ─────────────────────────────────────────────────────────────
_TESTS_DIR = Path(__file__).resolve().parent
_ML_DIR = _TESTS_DIR.parent
_ROOT = _ML_DIR.parent
_BACKEND = _ROOT / "backend"

for p in [str(_ROOT), str(_ML_DIR), str(_BACKEND)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from InSight_ML.complaint_extraction import extract_complaint_span
from InSight_ML.validation import (
    validate_cosmetics_df,
    validate_custom_csv,
    verify_complaint_spans,
    Issue,
)
from InSight_ML.pipeline_config import (
    ARTIFACTS, DATASETS, SEVERITY, PSI, PROVISIONAL_THEME_NAMES,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_cosmetics_df(n: int = 10, extra_cols: bool = False) -> pd.DataFrame:
    """Create a minimal valid cosmetics DataFrame for testing."""
    data = {
        "review_text": [f"This is review number {i}. Great product!" for i in range(n)],
        "product_id": [f"P{i:05d}" for i in range(n)],
        "product_name": [f"Product {i}" for i in range(n)],
        "brand_name": [f"Brand {i % 3}" for i in range(n)],
        "rating": [float((i % 5) + 1) for i in range(n)],
        "submission_time": [f"2021-0{(i % 9) + 1}-01" for i in range(n)],
    }
    if extra_cols:
        data["weak_sentiment"] = ["positive"] * n
        data["word_count"] = [10] * n
    df = pd.DataFrame(data)
    return df


# =============================================================================
# Test Group 1: Complaint Extraction
# =============================================================================

class TestComplaintExtractionCorrectness(unittest.TestCase):
    """Verify the regex works correctly after the double-escape fix."""

    def _assert_detected(self, text: str, should_detect: bool, msg: str = ""):
        result = extract_complaint_span(text)
        self.assertEqual(
            result["detected"], should_detect,
            f"Expected detected={should_detect} for: {repr(text[:60])}. {msg}"
        )

    def test_discourse_markers_detected(self):
        """Discourse markers must trigger detection."""
        triggers = [
            "Great product but it leaked all over",
            "I liked it however the pump broke",
            "Good scent although it caused stinging",
            "Works well except that it jammed",
            "Unfortunately the cream burned my skin",
        ]
        for text in triggers:
            self._assert_detected(text, True, "discourse marker should trigger")

    def test_defect_keywords_detected(self):
        """Physical defect keywords must trigger detection."""
        triggers = [
            "The bottle cracked during shipping",
            "Pump is jammed, nothing comes out",
            "The serum leaked all over the box",
            "This caused burning and redness",
            "I got a rash after one use",
            "The app crashes on startup",
        ]
        for text in triggers:
            self._assert_detected(text, True, "defect keyword should trigger")

    def test_clean_positive_not_detected(self):
        """Clean positive reviews must not trigger detection."""
        clean = [
            "Absolutely love this moisturizer! Skin feels amazing.",
            "Fast delivery and great packaging. Five stars!",
            "My skin has never looked better. Will repurchase.",
            "Perfect hydration, no greasy residue.",
        ]
        for text in clean:
            self._assert_detected(text, False, "positive review should not trigger")

    def test_empty_and_invalid_inputs(self):
        """Empty string, whitespace-only, and non-string must return detected=False."""
        for inp in ["", "   ", "\n\t", None]:
            result = extract_complaint_span(inp)  # type: ignore[arg-type]
            self.assertFalse(result["detected"], f"Expected no detection for: {repr(inp)}")
            self.assertEqual(result["text"], "")
            self.assertIsNone(result["start"])
            self.assertIsNone(result["end"])

    def test_span_offsets_exact_match(self):
        """When detected, text[start:end] must exactly equal span['text']."""
        test_cases = [
            "I love this serum but it leaked in the box",
            "Good product however the pump is completely jammed",
            "Unfortunately the serum burned my cheeks",
            "App crashes constantly since the last update",
        ]
        for text in test_cases:
            result = extract_complaint_span(text)
            if result["detected"]:
                start = result["start"]
                end = result["end"]
                span_text = result["text"]
                self.assertIsInstance(start, int)
                self.assertIsInstance(end, int)
                self.assertTrue(0 <= start < end <= len(text),
                                f"Offsets [{start}:{end}] out of range for text len={len(text)}")
                self.assertEqual(
                    text[start:end], span_text,
                    f"text[{start}:{end}] != span_text for: {repr(text[:60])}"
                )

    def test_case_insensitivity(self):
        """Pattern must match regardless of case."""
        for text in [
            "The bottle CRACKED during shipping",
            "Unfortunately this BURNED my face",
            "BUT it leaked everywhere",
            "TERRIBLE smell, makes me nauseous",
        ]:
            self._assert_detected(text, True, "case-insensitive match expected")

    def test_no_false_positive_but_in_word(self):
        """'but' should only trigger on word boundary, not as part of 'butter'."""
        # 'butter' contains 'but' but 'but' at word boundary should still match
        # if there is a standalone 'but' elsewhere
        text_no_standalone_but = "I love the buttery texture of this cream"
        result = extract_complaint_span(text_no_standalone_but)
        # 'butter' starts with 'but' but \b means it should not match 'butter'
        self.assertFalse(result["detected"],
                         "Should not match 'but' inside 'butter' due to word boundary")

    def test_latency_per_review(self):
        """Average extraction time should be < 5ms per review."""
        texts = [
            "Great product but the pump leaked",
            "Absolutely love this moisturizer",
            "Unfortunately it burned my skin",
            "Perfect for dry skin, no complaints",
        ] * 25  # 100 reviews
        t0 = time.time()
        for t in texts:
            extract_complaint_span(t)
        avg_ms = (time.time() - t0) / len(texts) * 1000
        self.assertLess(avg_ms, 5.0, f"Avg latency {avg_ms:.2f}ms exceeds 5ms threshold")


# =============================================================================
# Test Group 2: Validation Module
# =============================================================================

class TestValidationModule(unittest.TestCase):

    def test_valid_cosmetics_df_passes(self):
        """A well-formed DataFrame must pass with no ERROR issues."""
        df = _make_cosmetics_df(20, extra_cols=True)
        result = validate_cosmetics_df(df)
        self.assertFalse(result.has_errors, f"Expected no errors: {result.issues}")
        self.assertEqual(result.n_valid, 20)
        self.assertEqual(result.n_rejected, 0)

    def test_missing_required_column_raises_error(self):
        """DataFrame missing a required column must produce an ERROR."""
        df = _make_cosmetics_df(10)
        df = df.drop(columns=["rating"])
        result = validate_cosmetics_df(df)
        self.assertTrue(result.has_errors)
        self.assertEqual(result.n_valid, 0)

    def test_empty_review_text_rejected(self):
        """Rows with empty review_text must be excluded."""
        df = _make_cosmetics_df(10)
        df.loc[0, "review_text"] = ""
        df.loc[1, "review_text"] = "   "
        result = validate_cosmetics_df(df)
        self.assertEqual(result.n_rejected, 2)
        self.assertEqual(result.n_valid, 8)

    def test_invalid_rating_is_warning_not_error(self):
        """Out-of-range ratings produce a WARNING, not an ERROR (row not rejected)."""
        df = _make_cosmetics_df(10)
        df.loc[0, "rating"] = 6.0  # invalid
        df.loc[1, "rating"] = 0.0  # invalid
        result = validate_cosmetics_df(df)
        warning_checks = [i.check for i in result.issues if i.level == "WARNING"]
        self.assertIn("invalid_rating_range", warning_checks)
        self.assertFalse(result.has_errors)

    def test_duplicate_texts_deduplicated(self):
        """Duplicate review_text rows must be reduced to one each."""
        df = _make_cosmetics_df(10)
        df.loc[5, "review_text"] = df.loc[0, "review_text"]  # make row 5 a dup of row 0
        result = validate_cosmetics_df(df)
        self.assertEqual(result.n_valid, 9)  # one duplicate removed
        warning_checks = [i.check for i in result.issues if i.level == "WARNING"]
        self.assertIn("duplicate_review_text", warning_checks)

    def test_unexpected_columns_is_info_not_error(self):
        """Extra columns produce INFO, not ERROR."""
        df = _make_cosmetics_df(5)
        df["unexpected_column"] = "test"
        result = validate_cosmetics_df(df)
        info_checks = [i.check for i in result.issues if i.level == "INFO"]
        self.assertIn("unexpected_columns", info_checks)
        self.assertFalse(result.has_errors)

    def test_custom_csv_validator_basic(self):
        """Generic CSV validator must accept a basic valid DataFrame."""
        df = pd.DataFrame({
            "review": ["Good product", "Bad experience", "Average quality"],
            "score": [5, 1, 3],
        })
        result = validate_custom_csv(df, text_col="review", rating_col="score")
        self.assertFalse(result.has_errors)
        self.assertEqual(result.n_valid, 3)

    def test_custom_csv_missing_text_col_error(self):
        """Custom CSV validator must error if text column is missing."""
        df = pd.DataFrame({"score": [1, 2, 3]})
        result = validate_custom_csv(df, text_col="review")
        self.assertTrue(result.has_errors)

    def test_span_verification_valid_spans(self):
        """verify_complaint_spans must return no issues for correct offsets."""
        texts = [
            "Great product but it leaked",
            "Clean positive review",
        ]
        spans = [
            extract_complaint_span(texts[0]),
            extract_complaint_span(texts[1]),
        ]
        issues = verify_complaint_spans(spans, texts)
        self.assertEqual(len(issues), 0, f"Unexpected issues: {issues}")

    def test_span_verification_catches_bad_offsets(self):
        """verify_complaint_spans must catch manually corrupted offsets."""
        spans = [
            {"detected": True, "text": "but it leaked", "start": -1, "end": 5},
            {"detected": True, "text": "match", "start": 100, "end": 50},
        ]
        source_texts = ["Great product but it leaked", "source"]
        issues = verify_complaint_spans(spans, source_texts)
        error_checks = [i.check for i in issues if i.level == "ERROR"]
        self.assertIn("invalid_span_offsets", error_checks)

    def test_span_verification_catches_text_mismatch(self):
        """verify_complaint_spans must catch spans where text != source[start:end]."""
        text = "Great product but it leaked"
        result = extract_complaint_span(text)
        # Tamper with the span text
        result["text"] = "WRONG TEXT"
        issues = verify_complaint_spans([result], [text])
        error_checks = [i.check for i in issues if i.level == "ERROR"]
        self.assertIn("span_text_offset_mismatch", error_checks)


# =============================================================================
# Test Group 3: Sentiment Pipeline (offline artifact)
# =============================================================================

class TestSentimentPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import joblib
        pipeline_path = ARTIFACTS["sentiment_pipeline"]
        if not pipeline_path.exists():
            raise unittest.SkipTest(f"Sentiment pipeline artifact not found: {pipeline_path}")
        cls.pipeline = joblib.load(pipeline_path)

    def test_pipeline_classes(self):
        """Pipeline must have exactly 3 classes: negative, neutral, positive."""
        classes = [str(c).lower() for c in self.pipeline.classes_]
        self.assertEqual(set(classes), {"negative", "neutral", "positive"})

    def test_predict_positive(self):
        """Clearly positive text should predict positive."""
        texts = [
            "Absolutely love this product! My skin has never felt better.",
            "Amazing moisturizer, highly recommend to everyone.",
        ]
        preds = [str(p).lower() for p in self.pipeline.predict(texts)]
        self.assertTrue(
            all(p == "positive" for p in preds),
            f"Expected all positive, got: {preds}"
        )

    def test_predict_negative(self):
        """Clearly negative text should predict negative."""
        texts = [
            "Terrible product, caused horrible rash and burned my skin.",
            "Completely useless, pump is jammed, leaked everywhere. Awful.",
        ]
        preds = [str(p).lower() for p in self.pipeline.predict(texts)]
        self.assertTrue(
            all(p == "negative" for p in preds),
            f"Expected all negative, got: {preds}"
        )

    def test_predict_proba_sums_to_one(self):
        """Probability outputs must sum to ~1.0 per row."""
        texts = ["Good product", "Terrible experience", "Average, nothing special"]
        probs = self.pipeline.predict_proba(texts)
        for i, row in enumerate(probs):
            self.assertAlmostEqual(
                float(np.sum(row)), 1.0, places=5,
                msg=f"Probabilities for row {i} sum to {np.sum(row):.6f}, not 1.0"
            )

    def test_throughput(self):
        """Throughput should be at least 500 reviews/sec on the loaded model.

        Guard against ZeroDivisionError on very fast hardware where
        elapsed rounds to 0.0 by using a minimum floor of 1 microsecond.
        """
        texts = ["Great product I love it" for _ in range(500)]  # larger batch for stable timing
        t0 = time.time()
        _ = self.pipeline.predict(texts)
        elapsed = max(time.time() - t0, 1e-6)  # floor prevents ZeroDivisionError
        throughput = len(texts) / elapsed
        self.assertGreater(throughput, 500, f"Throughput too low: {throughput:.0f} rev/sec")


# =============================================================================
# Test Group 4: Theme Assignment (cluster artifacts)
# =============================================================================

class TestThemeArtifacts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        assign_path = ARTIFACTS["cluster_assignments"]
        if not assign_path.exists():
            raise unittest.SkipTest(f"Cluster assignments not found: {assign_path}")
        cls.df_assign = pd.read_csv(assign_path)
        cls.centroids_path = ARTIFACTS["theme_centroids"]

    def test_assignment_row_count(self):
        """Cluster assignments must have exactly 10,000 rows."""
        self.assertEqual(len(self.df_assign), 10000,
                         f"Expected 10000 rows, got {len(self.df_assign)}")

    def test_assignment_cluster_range(self):
        """All cluster IDs must be in [0, 5]."""
        ids = self.df_assign["minilm_cluster_k6"].unique()
        self.assertEqual(set(ids), {0, 1, 2, 3, 4, 5},
                         f"Unexpected cluster IDs: {sorted(ids)}")

    def test_no_empty_clusters(self):
        """Every cluster 0-5 must have at least 1 review assigned."""
        counts = self.df_assign["minilm_cluster_k6"].value_counts()
        for c in range(6):
            self.assertIn(c, counts.index, f"Cluster {c} is empty")
            self.assertGreater(counts[c], 0, f"Cluster {c} has 0 reviews")

    def test_theme_centroids_shape_and_norms(self):
        """Centroids must be (6, 384) and unit-normalized."""
        if not self.centroids_path.exists():
            self.skipTest("theme_centroids.npy not found")
        centroids = np.load(str(self.centroids_path))
        self.assertEqual(centroids.shape, (6, 384),
                         f"Expected shape (6, 384), got {centroids.shape}")
        norms = np.linalg.norm(centroids, axis=1)
        np.testing.assert_allclose(norms, np.ones(6), atol=1e-5,
                                   err_msg="Centroids are not unit-normalized")

    def test_provisional_theme_names_complete(self):
        """All 6 cluster IDs must have a provisional theme name."""
        self.assertEqual(len(PROVISIONAL_THEME_NAMES), 6)
        for c in range(6):
            self.assertIn(c, PROVISIONAL_THEME_NAMES)
            self.assertIsInstance(PROVISIONAL_THEME_NAMES[c], str)
            self.assertGreater(len(PROVISIONAL_THEME_NAMES[c]), 0)


# =============================================================================
# Test Group 5: Drift Detector
# =============================================================================

class TestDriftDetector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Import here to avoid heavy backend imports at module level
        sys.path.insert(0, str(_BACKEND))
        from app.ml.drift import TemporalDriftDetector
        cls.detector = TemporalDriftDetector()

    def _make_reviews(self, n_per_batch: int = 50) -> list:
        """Create synthetic review records for drift testing.

        The drift detector measures PSI on THEME distributions, not sentiment.
        The final batch (Q3) has a completely different theme distribution to
        ensure PSI >> 0.25 and trigger an alert.
        """
        records = []
        batches = ["2021-Q1", "2021-Q2", "2021-Q3"]
        for b_idx, batch in enumerate(batches):
            for i in range(n_per_batch):
                if batch == "2021-Q3":
                    # New dominant theme not seen before → large PSI
                    theme = "Crisis Theme" if i < int(n_per_batch * 0.9) else "Test Theme A"
                    sent = "NEGATIVE" if i < int(n_per_batch * 0.8) else "POSITIVE"
                else:
                    # Stable Q1/Q2: two themes roughly 50/50
                    theme = "Test Theme A" if i % 2 == 0 else "Test Theme B"
                    sent = "POSITIVE" if i < int(n_per_batch * 0.7) else "NEGATIVE"
                records.append({
                    "id": f"TEST-{b_idx:02d}-{i:03d}",
                    "batch_or_version": batch,
                    "sentiment_pred": sent,
                    "theme_title": theme,
                })
        return records

    def test_timeline_structure(self):
        """Drift result must contain 'timeline', 'alerts', 'batches_analyzed'."""
        records = self._make_reviews()
        result = self.detector.analyze_drift(records)
        self.assertIn("timeline", result)
        self.assertIn("alerts", result)
        self.assertIn("batches_analyzed", result)

    def test_timeline_length(self):
        """Timeline must have one entry per distinct batch."""
        records = self._make_reviews()
        result = self.detector.analyze_drift(records)
        self.assertEqual(result["batches_analyzed"], 3)
        self.assertEqual(len(result["timeline"]), 3)

    def test_psi_calculation_stable(self):
        """First batch has no prior → PSI should be 0."""
        records = self._make_reviews()
        result = self.detector.analyze_drift(records)
        first_entry = result["timeline"][0]
        self.assertEqual(first_entry["psi"], 0.0)

    def test_drift_alert_on_negative_surge(self):
        """A dominant new theme in Q3 must produce at least one drift alert.

        The drift detector measures PSI on theme distributions. When a new theme
        dominates Q3 (90% of reviews) vs Q2 (0%), PSI >> 0.25 → CRITICAL alert.
        """
        records = self._make_reviews(n_per_batch=200)
        result = self.detector.analyze_drift(records)
        self.assertGreater(len(result["alerts"]), 0,
                           "Expected at least one drift alert when Q3 has a completely new dominant theme")

    def test_psi_formula_correctness(self):
        """Manual PSI verification: PSI(A, A) = 0."""
        from app.ml.drift import TemporalDriftDetector
        baseline = {"A": 50, "B": 30, "C": 20}
        psi = TemporalDriftDetector.calculate_psi(baseline, baseline)
        self.assertAlmostEqual(psi, 0.0, places=3,
                               msg=f"PSI(A, A) should be ~0, got {psi:.6f}")

    def test_psi_positive(self):
        """PSI between very different distributions must be positive."""
        from app.ml.drift import TemporalDriftDetector
        baseline = {"A": 100, "B": 0, "C": 0}
        target = {"A": 0, "B": 0, "C": 100}
        psi = TemporalDriftDetector.calculate_psi(baseline, target)
        self.assertGreater(psi, 0.0, f"PSI should be positive for divergent distributions, got {psi}")


# =============================================================================
# Test Group 6: Pipeline Config and Thresholds
# =============================================================================

class TestPipelineConfig(unittest.TestCase):

    def test_severity_thresholds_ordered(self):
        """Severity thresholds must be logically ordered."""
        self.assertGreater(SEVERITY["critical_neg_fraction"], SEVERITY["medium_neg_fraction"])
        self.assertGreater(SEVERITY["high_neg_fraction"], SEVERITY["medium_neg_fraction"])
        self.assertGreater(SEVERITY["critical_min_volume"], 0)

    def test_psi_thresholds_ordered(self):
        """PSI thresholds must be logically ordered."""
        self.assertGreater(PSI["critical_threshold"], PSI["moderate_threshold"])
        self.assertGreater(PSI["moderate_threshold"], 0)

    def test_all_artifacts_paths_exist(self):
        """All critical artifact paths must exist on disk."""
        critical_artifacts = [
            "sentiment_pipeline",
            "cluster_assignments",
            "cluster_representatives",
            "theme_centroids",
        ]
        for key in critical_artifacts:
            path = ARTIFACTS[key]
            self.assertTrue(
                Path(path).exists(),
                f"Artifact '{key}' not found at: {path}"
            )

    def test_primary_dataset_exists(self):
        """Primary cosmetics dataset must exist on disk."""
        path = DATASETS["cosmetics_10k"]
        self.assertTrue(Path(path).exists(), f"Dataset not found: {path}")


# =============================================================================
# Test Group 7: End-to-End Pipeline Integration
# =============================================================================

class TestEndToEndPipeline(unittest.TestCase):
    """
    Full pipeline integration test using the real cosmetics dataset.

    This test is heavier (~30-60 seconds) but validates the complete
    data flow from CSV → validation → PII → sentiment → themes → drift → output.
    """

    @classmethod
    def setUpClass(cls):
        # Guard: skip if any artifact is missing
        missing = []
        for key in ["sentiment_pipeline", "cluster_assignments", "cluster_representatives", "theme_centroids"]:
            if not ARTIFACTS[key].exists():
                missing.append(key)
        if missing:
            raise unittest.SkipTest(f"Skipping E2E test: missing artifacts: {missing}")
        if not DATASETS["cosmetics_10k"].exists():
            raise unittest.SkipTest(f"Skipping E2E test: dataset missing: {DATASETS['cosmetics_10k']}")

        import tempfile
        cls.output_dir = Path(tempfile.mkdtemp(prefix="insight_test_"))

        from InSight_ML.run_pipeline import run_pipeline
        import logging
        logging.getLogger("insight.pipeline").setLevel(logging.WARNING)
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

        t0 = time.time()
        cls.summary = run_pipeline(
            dataset_path=DATASETS["cosmetics_10k"],
            output_dir=cls.output_dir,
        )
        cls.elapsed = time.time() - t0

        # Load outputs for inspection
        import json
        with open(cls.output_dir / "reviews_latest.json", encoding="utf-8") as f:
            cls.records = json.load(f)
        with open(cls.output_dir / "themes_latest.json", encoding="utf-8") as f:
            cls.themes = json.load(f)
        with open(cls.output_dir / "drift_latest.json", encoding="utf-8") as f:
            cls.drift = json.load(f)

    def test_pipeline_succeeded(self):
        """Pipeline must complete with status SUCCESS."""
        self.assertEqual(self.summary["status"], "SUCCESS",
                         f"Pipeline failed: {self.summary.get('reason')}")

    def test_row_counts(self):
        """Output should have 9990 records.

        Known fact: cosmetics_10k.csv contains 10 duplicate review_text values.
        Validation correctly removes them, yielding 9990 unique, valid records.
        This test documents that known data quality characteristic.
        """
        self.assertEqual(self.summary["n_valid_rows"], 9990,
                         f"Expected 9990, got {self.summary['n_valid_rows']}")
        self.assertEqual(len(self.records), 9990,
                         f"Output JSON has {len(self.records)} records, expected 9990")

    def test_no_rejected_rows(self):
        """Exactly 10 duplicate rows (known) should be rejected, no more.

        cosmetics_10k.csv has 10 known duplicate review_text entries.
        Validation removes duplicates (WARNING, not ERROR), so exactly 10
        rows should be rejected and the rest accepted without errors.
        """
        self.assertEqual(self.summary["n_rejected_rows"], 10,
                         f"Expected 10 rejected rows (known duplicates), got {self.summary['n_rejected_rows']}")
        self.assertFalse(self.summary.get("validation_has_errors", False),
                         "Rejection should be due to WARNING (duplicates), not ERROR")

    def test_record_ids_unique(self):
        """All record IDs must be unique."""
        ids = [r["id"] for r in self.records]
        self.assertEqual(len(set(ids)), len(ids),
                         f"{len(ids) - len(set(ids))} duplicate IDs found")

    def test_record_schema(self):
        """Every record must contain all required fields."""
        required = [
            "id", "pipeline_version", "domain", "product_id", "product_name",
            "brand_name", "sku_or_module", "batch_or_version", "channel", "rating",
            "redacted_text", "pii_detected",
            "sentiment_pred", "sentiment_confidence", "sentiment_is_provisional",
            "cluster_id", "theme_title", "theme_is_provisional",
            "highlight_span", "complaint_is_provisional",
            "sentences",           # NEW: sentence-level classification results
            "source_row_index",
        ]
        sample = self.records[0]
        for key in required:
            self.assertIn(key, sample, f"Missing required field: {key}")

    def test_raw_text_not_in_output(self):
        """raw_text must NOT be persisted in the output JSON (PII risk)."""
        for r in self.records[:20]:
            self.assertNotIn("raw_text", r,
                             "raw_text (PII source) should not appear in pipeline output JSON")

    def test_sentiment_distribution_sane(self):
        """Sentiment distribution must be non-trivial."""
        dist = self.summary["sentiment_distribution"]
        for cls in ["POSITIVE", "NEUTRAL", "NEGATIVE"]:
            self.assertIn(cls, dist)
            self.assertGreater(dist[cls], 0, f"Class {cls} has zero predictions")
        # Positive should dominate (known property of Sephora dataset)
        self.assertGreater(dist["POSITIVE"], dist["NEGATIVE"],
                           "POSITIVE should exceed NEGATIVE for Sephora dataset")

    def test_all_cluster_ids_valid(self):
        """All cluster_id values must be in [0, 5]."""
        bad = [r for r in self.records if r["cluster_id"] not in range(6)]
        self.assertEqual(len(bad), 0,
                         f"{len(bad)} records have invalid cluster_id")

    def test_all_6_clusters_populated(self):
        """All 6 clusters must have at least 1 record assigned."""
        cluster_dist = Counter(r["cluster_id"] for r in self.records)
        for c in range(6):
            self.assertIn(c, cluster_dist, f"Cluster {c} has no records")
            self.assertGreater(cluster_dist[c], 0)

    def test_span_offsets_all_valid(self):
        """All detected complaint spans must have valid offsets."""
        n_invalid = 0
        n_mismatch = 0
        for r in self.records:
            span = r.get("highlight_span", {})
            if not span.get("detected"):
                continue
            src = r["redacted_text"]
            start = span.get("start")
            end = span.get("end")
            span_text = span.get("text", "")
            if not (isinstance(start, int) and isinstance(end, int)):
                n_invalid += 1
                continue
            if not (0 <= start < end <= len(src)):
                n_invalid += 1
                continue
            if src[start:end] != span_text:
                n_mismatch += 1
        self.assertEqual(n_invalid, 0, f"{n_invalid} spans have invalid offsets")
        self.assertEqual(n_mismatch, 0, f"{n_mismatch} spans have text/offset mismatch")

    def test_quarterly_cohort_format(self):
        """All batch_or_version values must match YYYY-Q# format."""
        import re
        cohort_re = re.compile(r"^\d{4}-Q[1-4]$")
        bad = [r["batch_or_version"] for r in self.records if not cohort_re.match(r["batch_or_version"])]
        # Some records may have 'unknown' if submission_time was unparseable
        bad_not_unknown = [b for b in bad if b != "unknown"]
        self.assertEqual(len(bad_not_unknown), 0,
                         f"Unexpected cohort format: {set(bad_not_unknown)}")

    def test_themes_count(self):
        """Must produce exactly 6 themes."""
        self.assertEqual(len(self.themes), 6,
                         f"Expected 6 themes, got {len(self.themes)}")

    def test_themes_schema(self):
        """Each theme must have all required keys."""
        required = [
            "cluster_id", "title", "keywords", "severity", "severity_note",
            "review_count", "sentiment_distribution", "negative_rate", "sample_verbatims",
        ]
        for t in self.themes:
            for key in required:
                self.assertIn(key, t, f"Theme missing key: {key}")
            self.assertIn(t["severity"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])

    def test_drift_timeline(self):
        """Drift timeline must cover multiple cohorts."""
        timeline = self.drift.get("timeline", [])
        self.assertGreater(len(timeline), 1, "Drift timeline must have more than one cohort")
        for entry in timeline:
            self.assertIn("batch_or_version", entry)
            self.assertIn("review_count", entry)
            self.assertIn("psi", entry)
            self.assertGreaterEqual(entry["psi"], 0.0)

    def test_throughput_acceptable(self):
        """Full pipeline throughput should exceed 50 reviews/sec.

        NOTE: Pipeline v1.2.0 adds sentence-level MiniLM encoding (Stage 6a)
        on ~43k extracted sentences and MiniBatchKMeans complaint clustering
        (Stage 6b). These are CPU-bound neural inference steps that dominate
        total wall-clock time. The threshold was recalibrated from 200 rev/sec
        (old regex-only pipeline) to 50 rev/sec. Measured throughput on this
        machine: ~113 rev/sec. A floor of 50 still catches runaway regressions.
        """
        throughput = self.summary.get("throughput_reviews_per_sec", 0)
        self.assertGreater(throughput, 50,
                           f"Pipeline throughput {throughput:.0f} rev/sec is too low")

    def test_provisional_notices_present(self):
        """Summary must include provisional_notices list."""
        notices = self.summary.get("provisional_notices", [])
        self.assertIsInstance(notices, list)
        self.assertGreater(len(notices), 0)

    def test_sentence_pipeline_ran(self):
        """Summary must report positive sentence counts from Stage 6a."""
        n_total = self.summary.get("n_sentences_total", 0)
        self.assertGreater(n_total, 0, "n_sentences_total must be > 0")

    def test_sentence_complaint_pool_not_empty(self):
        """Complaint sentence pool must be non-empty on cosmetics data."""
        n_complaints = self.summary.get("n_sentence_complaints", 0)
        self.assertGreater(n_complaints, 0, "n_sentence_complaints must be > 0")

    def test_complaint_clusters_produced(self):
        """Complaint clustering (Stage 6b) must produce at least 2 clusters."""
        n_clusters = self.summary.get("n_complaint_clusters", 0)
        self.assertGreaterEqual(n_clusters, 2,
                                f"Expected ≥2 complaint clusters, got {n_clusters}")


# =============================================================================
# Test Group 8: PII Redactor
# =============================================================================

class TestPIIRedactor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app.core.pii import PIIRedactor
        cls.redactor = PIIRedactor()

    def test_email_redacted(self):
        text = "Please contact me at user@example.com for questions"
        redacted, tags = self.redactor.redact(text)
        self.assertNotIn("user@example.com", redacted)
        self.assertIn("EMAIL", tags)
        self.assertIn("[REDACTED_EMAIL]", redacted)

    def test_phone_redacted(self):
        text = "Call me on +91-9876543210 to discuss"
        redacted, tags = self.redactor.redact(text)
        self.assertIn("PHONE", tags)

    def test_order_id_redacted(self):
        text = "My order reference is ORD-123456"
        redacted, tags = self.redactor.redact(text)
        self.assertIn("ORDER_ID", tags)

    def test_clean_text_unchanged(self):
        text = "Great moisturizer, very hydrating and gentle on skin."
        redacted, tags = self.redactor.redact(text)
        self.assertEqual(redacted, text)
        self.assertEqual(tags, [])

    def test_empty_text_handled(self):
        redacted, tags = self.redactor.redact("")
        self.assertEqual(redacted, "")
        self.assertEqual(tags, [])

    def test_redacted_text_not_empty(self):
        """After redaction the text should have content (replacement placeholder)."""
        text = "Contact user@example.com for more info"
        redacted, _ = self.redactor.redact(text)
        self.assertGreater(len(redacted), 0)


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
