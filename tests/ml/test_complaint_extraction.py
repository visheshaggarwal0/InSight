"""test_complaint_extraction.py
Tests complaint span extraction on real cosmetics review data.

Uses the pre-processed cosmetics_10k.csv dataset (real Sephora reviews)
instead of synthetic data, for more realistic coverage testing.
"""

import os
import sys
import time
import unittest

# ── Path setup ───────────────────────────────────────────────────────────────
_TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
_ROOT = os.path.abspath(os.path.join(_TESTS_DIR, "..", ".."))
_BACKEND = os.path.join(_ROOT, "backend")
for p in [_ROOT, _BACKEND]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
from app.ml.complaint_extraction import extract_complaint_span
from app.ml.pipeline_config import DATASETS


class TestComplaintExtractionOnRealData(unittest.TestCase):
    """Runs complaint extraction tests against real Sephora cosmetics reviews."""

    @classmethod
    def setUpClass(cls):
        dataset_path = DATASETS["cosmetics_10k"]
        if not dataset_path.exists():
            raise unittest.SkipTest(f"Real dataset not found: {dataset_path}")
        df = pd.read_csv(dataset_path)
        # Use first 500 reviews for a fast but representative test
        cls.sample = df["review_text"].dropna().astype(str).head(500).tolist()

    def test_extraction_substrings(self):
        """When detected, text[start:end] must exactly match span['text']."""
        n_detected = 0
        for review in self.sample:
            result = extract_complaint_span(review)
            if result["detected"]:
                n_detected += 1
                start = result["start"]
                end = result["end"]
                span_text = result["text"]
                self.assertIsInstance(start, int)
                self.assertIsInstance(end, int)
                self.assertTrue(0 <= start < len(review),
                                f"start={start} out of range for text len={len(review)}")
                self.assertTrue(start < end <= len(review),
                                f"end={end} out of range: start={start}, len={len(review)}")
                self.assertEqual(
                    review[start:end], span_text,
                    f"text[{start}:{end}] != span_text"
                )
            else:
                self.assertEqual(result["text"], "")
                self.assertIsNone(result["start"])
                self.assertIsNone(result["end"])

        # Report coverage (informational — no threshold enforced on real data
        # since ground truth labels are unavailable)
        detection_rate = n_detected / len(self.sample) * 100
        print(f"\n[INFO] Complaint detection on real data: "
              f"{n_detected}/{len(self.sample)} ({detection_rate:.1f}%)")
        print("       NOTE: No precision/recall available without ground truth labels.")

    def test_latency(self):
        """Average extraction time over real reviews must be <5ms per review."""
        t0 = time.time()
        for review in self.sample:
            extract_complaint_span(review)
        elapsed = time.time() - t0
        avg_ms = (elapsed / len(self.sample)) * 1000
        self.assertLess(avg_ms, 5.0,
                        f"Average latency too high: {avg_ms:.2f}ms (threshold: 5ms)")

    def test_no_detection_on_clean_positive(self):
        """Canonical clean positive reviews must not trigger detection."""
        clean_reviews = [
            "Absolutely love this moisturizer! Skin feels amazing.",
            "Fast delivery and great packaging. Five stars!",
            "My skin has never looked better. Will repurchase.",
            "Perfect hydration, no greasy residue.",
            "Best eye cream I have ever tried. Very gentle.",
        ]
        for text in clean_reviews:
            result = extract_complaint_span(text)
            self.assertFalse(
                result["detected"],
                f"False positive on clean review: {repr(text)}"
            )

    def test_offsets_valid_on_trigger_sentences(self):
        """Canonical complaint trigger sentences must produce valid offsets."""
        complaint_texts = [
            "Great product but it leaked all over the box",
            "I liked it however the pump broke after two uses",
            "Unfortunately this caused terrible burning on my face",
            "Works well except that it jammed after one week",
        ]
        for text in complaint_texts:
            result = extract_complaint_span(text)
            if result["detected"]:
                start, end = result["start"], result["end"]
                self.assertEqual(text[start:end], result["text"],
                                 f"Offset mismatch for: {repr(text)}")


if __name__ == "__main__":
    unittest.main()
