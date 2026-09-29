import unittest
import pandas as pd
import os
import sys
import time
# Ensure project root is on sys.path for backend imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))  # add backend for app import
from InSight_ML.complaint_extraction import extract_complaint_span
# Alias backend's app package to top-level 'app' for internal imports
import importlib, sys as _sys
_app_pkg = importlib.import_module('backend.app')
_sys.modules.setdefault('app', _app_pkg)
from backend.app.data.datasets import TelemetryDatasetManager

class TestComplaintExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the same generated gold‑standard sample as the validation pipeline.
        # TelemetryDatasetManager.generate_d2c_cosmetics() returns (reviews, gold_sample).
        # The gold_sample contains the redacted_text field that the extractor expects.
        _, gold_sample = TelemetryDatasetManager.generate_d2c_cosmetics()
        # Take the first 100 entries for a quick reproducible test.
        cls.sample = [rec["redacted_text"] for rec in gold_sample[:100]]

    def test_extraction_substrings(self):
        for review in self.sample:
            result = extract_complaint_span(review)
            if result['detected']:
                span = result['text']
                start = result['start']
                end = result['end']
                # Verify indices are within bounds
                self.assertIsInstance(start, int)
                self.assertIsInstance(end, int)
                self.assertTrue(0 <= start < len(review))
                self.assertTrue(start < end <= len(review))
                # Verify exact substring match
                self.assertEqual(review[start:end], span)
            else:
                # When not detected, span should be empty and offsets None
                self.assertEqual(result['text'], "")
                self.assertIsNone(result['start'])
                self.assertIsNone(result['end'])

    def test_latency(self):
        # Measure average extraction time over the sample
        start_time = time.time()
        for review in self.sample:
            extract_complaint_span(review)
        total = time.time() - start_time
        avg_ms = (total / len(self.sample)) * 1000
        # Ensure average latency is reasonable (<5 ms per review)
        self.assertLess(avg_ms, 5, f"Average latency too high: {avg_ms:.2f} ms")

if __name__ == '__main__':
    unittest.main()
