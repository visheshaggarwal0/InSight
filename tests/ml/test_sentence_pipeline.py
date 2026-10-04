"""test_sentence_pipeline.py
Tests for the new sentence-level pipeline components:

  Group 1 : SentenceDeconstructor — offset invariant, word count filtering
  Group 2 : SentenceClassifier    — COMPLAINT/RECOMMENDATION/PRAISE/NOISE
  Group 3 : Router                — pool partitioning and traceability
  Group 4 : ComplaintClustering   — MiniLM embedding dims, c-TF-IDF, verbatim spans
  Group 5 : EndToEnd              — sentence pipeline on real cosmetics reviews

All existing tests in test_pipeline_integration.py and test_complaint_extraction.py
are preserved and are run alongside these tests.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
_TESTS = Path(__file__).resolve().parent
_ROOT = _TESTS.parent.parent
_BACKEND = _ROOT / "backend"

for p in [str(_ROOT), str(_BACKEND)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd

from app.ml.sentence_pipeline import (
    deconstruct_sentences,
    classify_and_route_review,
    classify_and_route_corpus,
    SentenceRecord,
    RoutedPools,
    LABEL_COMPLAINT,
    LABEL_RECOMMENDATION,
    LABEL_PRAISE,
    LABEL_NOISE,
    LABEL_PRAISE_NOISE,
)
from app.ml.pipeline_config import DATASETS


# =============================================================================
# Shared fixtures
# =============================================================================

_REVIEW_COMPLAINT = (
    "I love the moisturizer overall. However, the pump broke after two days "
    "and leaked product everywhere. Terrible quality control on this batch."
)
_REVIEW_RECOMMENDATION = (
    "The serum is nice. I would love if they added SPF protection. "
    "It would be great to see a travel size version in the future."
)
_REVIEW_PRAISE = (
    "Absolutely love this product! My skin has never felt so soft. "
    "Will definitely repurchase again."
)
_REVIEW_MIXED = (
    "Love the texture and scent. However, it caused terrible burning on my cheeks. "
    "I would suggest they reformulate without fragrance."
)


# =============================================================================
# Group 1: Sentence Deconstructor
# =============================================================================

class TestSentenceDeconstructor(unittest.TestCase):

    def _deconstruct(self, text: str, review_id: str = "REV-TEST-00001"):
        return deconstruct_sentences(review_id, 0, text)

    def test_offset_invariant(self):
        """text[start:end] must exactly equal sentence_text for every sentence."""
        text = _REVIEW_COMPLAINT
        sentences = self._deconstruct(text)
        for sent_text, start, end in sentences:
            self.assertEqual(
                text[start:end], sent_text,
                f"Offset invariant failed: text[{start}:{end}] != sentence"
            )

    def test_non_empty_sentences_returned(self):
        """Should return at least 1 sentence for a multi-sentence review."""
        sentences = self._deconstruct(_REVIEW_COMPLAINT)
        self.assertGreater(len(sentences), 0)

    def test_short_fragments_dropped(self):
        """Fragments shorter than min_word_count must be filtered out."""
        text = "Great. Amazing. I absolutely love this product so much it changed my skin."
        sentences = deconstruct_sentences("REV-X", 0, text, min_word_count=4)
        for sent_text, _, _ in sentences:
            word_count = len(sent_text.split())
            self.assertGreaterEqual(
                word_count, 4,
                f"Fragment shorter than min_word_count kept: {repr(sent_text)}"
            )

    def test_empty_text_returns_empty_list(self):
        """Empty or whitespace-only input must return an empty list."""
        for text in ["", "   ", "\n\t"]:
            result = deconstruct_sentences("REV-EMPTY", 0, text)
            self.assertEqual(result, [], f"Expected [] for empty input: {repr(text)}")

    def test_non_string_returns_empty_list(self):
        """Non-string input must return an empty list without raising."""
        result = deconstruct_sentences("REV-NONE", 0, None)  # type: ignore
        self.assertEqual(result, [])

    def test_sentence_ids_structure(self):
        """sentence_id must follow 'review_id::S###' format."""
        _, pools = classify_and_route_review("REV-TEST-00001", 0, _REVIEW_COMPLAINT)
        all_records: list[SentenceRecord] = (
            pools.complaint + pools.recommendation + pools.praise_noise
        )
        for rec in all_records:
            self.assertIn("::", rec.sentence_id)
            self.assertTrue(rec.sentence_id.startswith("REV-TEST-00001::S"))
            suffix = rec.sentence_id.split("::S")[1]
            self.assertTrue(suffix.isdigit(), f"sentence_id suffix not numeric: {suffix}")

    def test_offsets_cover_all_sentences(self):
        """All returned sentences must have start < end."""
        text = _REVIEW_MIXED
        for sent_text, start, end in deconstruct_sentences("REV-MIX", 0, text):
            self.assertLess(start, end, f"start >= end for sentence: {repr(sent_text)}")

    def test_latency_per_review(self):
        """Average deconstruction time must be < 2ms per review."""
        texts = [_REVIEW_COMPLAINT, _REVIEW_RECOMMENDATION, _REVIEW_PRAISE, _REVIEW_MIXED] * 50
        t0 = time.time()
        for i, text in enumerate(texts):
            deconstruct_sentences(f"REV-{i:04d}", i, text)
        avg_ms = (time.time() - t0) / len(texts) * 1000
        self.assertLess(avg_ms, 2.0, f"Average latency {avg_ms:.3f}ms exceeds 2ms")


# =============================================================================
# Group 2: Sentence Classifier
# =============================================================================

class TestSentenceClassifier(unittest.TestCase):

    def _classify(self, text: str):
        _, pools = classify_and_route_review("REV-CLS", 0, text)
        all_sents = pools.complaint + pools.recommendation + pools.praise_noise
        # Return labels of all sentences
        return [s.label for s in all_sents]

    def test_complaint_keywords_trigger_complaint(self):
        """Sentences with defect keywords must be classified COMPLAINT."""
        complaint_sentences = [
            "The pump broke completely and leaked everywhere.",
            "This caused terrible burning and redness on my skin.",
            "The bottle arrived cracked and the product spilled.",
            "Unfortunately the app crashed every time I logged in.",
        ]
        for sent in complaint_sentences:
            labels = self._classify(sent)
            self.assertIn(
                LABEL_COMPLAINT, labels,
                f"Expected COMPLAINT in labels for: {repr(sent)}"
            )

    def test_recommendation_patterns_trigger_recommendation(self):
        """Sentences expressing recommendations must be classified RECOMMENDATION."""
        rec_sentences = [
            "I would love if they added SPF protection to this serum.",
            "Please add a travel size option for this product.",
            "It would be great if they offered a fragrance-free version.",
            "They should include a pump dispenser in the next version.",
        ]
        for sent in rec_sentences:
            labels = self._classify(sent)
            self.assertIn(
                LABEL_RECOMMENDATION, labels,
                f"Expected RECOMMENDATION in labels for: {repr(sent)}"
            )

    def test_clean_positive_gets_praise_noise(self):
        """Purely positive sentences should be classified PRAISE/NOISE."""
        praise_sentences = [
            "Absolutely love this moisturizer! My skin feels amazing.",
            "Best eye cream I have ever tried.",
            "The texture is perfect and absorbs instantly.",
        ]
        for sent in praise_sentences:
            labels = self._classify(sent)
            # For a purely positive sentence, PRAISE should appear
            self.assertTrue(
                any(lbl in (LABEL_PRAISE, LABEL_PRAISE_NOISE) for lbl in labels),
                f"Expected PRAISE in labels for: {repr(sent)}"
            )

    def test_all_labels_are_valid(self):
        """Every sentence record must have a valid label."""
        valid_labels = {LABEL_COMPLAINT, LABEL_RECOMMENDATION, LABEL_PRAISE, LABEL_NOISE, LABEL_PRAISE_NOISE}
        for text in [_REVIEW_COMPLAINT, _REVIEW_RECOMMENDATION, _REVIEW_PRAISE, _REVIEW_MIXED]:
            all_sents, _ = classify_and_route_review("REV-LBL", 0, text)
            for rec in all_sents:
                self.assertIn(
                    rec.label, valid_labels,
                    f"Invalid label '{rec.label}' for sentence: {repr(rec.sentence_text[:60])}"
                )

    def test_confidence_in_range(self):
        """All confidence scores must be in [0.0, 1.0]."""
        all_sents, _ = classify_and_route_review("REV-CONF", 0, _REVIEW_MIXED)
        for rec in all_sents:
            self.assertGreaterEqual(rec.confidence, 0.0)
            self.assertLessEqual(rec.confidence, 1.0)

    def test_provisional_flag_always_true(self):
        """is_provisional must always be True for heuristic classifier output."""
        all_sents, _ = classify_and_route_review("REV-PROV", 0, _REVIEW_MIXED)
        for rec in all_sents:
            self.assertTrue(
                rec.is_provisional,
                f"is_provisional False for: {repr(rec.sentence_text[:60])}"
            )


# =============================================================================
# Group 3: Router — pool partitioning and traceability
# =============================================================================

class TestRouter(unittest.TestCase):

    def test_all_sentences_routed_exactly_once(self):
        """Every sentence must appear in exactly one pool."""
        all_sents, pools = classify_and_route_review("REV-ROUTE", 0, _REVIEW_MIXED)
        routed_ids = set(
            s.sentence_id for s in
            pools.complaint + pools.recommendation + pools.praise_noise
        )
        all_ids = set(s.sentence_id for s in all_sents)
        self.assertEqual(
            routed_ids, all_ids,
            "Some sentences appear in wrong pool or are missing from routing."
        )
        routed_total = (
            len(pools.complaint) + len(pools.recommendation) + len(pools.praise_noise)
        )
        self.assertEqual(routed_total, len(all_sents))

    def test_review_id_preserved_in_pool(self):
        """Every sentence in a pool must carry the source review_id."""
        rev_id = "REV-TRACE-00099"
        all_sents, pools = classify_and_route_review(rev_id, 42, _REVIEW_COMPLAINT)
        for pool in [pools.complaint, pools.recommendation, pools.praise_noise]:
            for rec in pool:
                self.assertEqual(rec.review_id, rev_id)

    def test_source_row_index_preserved(self):
        """source_row_index must equal the value passed in."""
        all_sents, pools = classify_and_route_review("REV-IDX", 777, _REVIEW_COMPLAINT)
        for rec in (pools.complaint + pools.recommendation + pools.praise_noise):
            self.assertEqual(rec.source_row_index, 777)

    def test_no_empty_sentence_text_in_pools(self):
        """No pool should contain a sentence with empty text."""
        _, pools = classify_and_route_review("REV-EMPTY", 0, _REVIEW_MIXED)
        for pool_name, pool in [("complaint", pools.complaint),
                                 ("recommendation", pools.recommendation),
                                 ("praise_noise", pools.praise_noise)]:
            for rec in pool:
                self.assertTrue(
                    rec.sentence_text.strip(),
                    f"Empty sentence in {pool_name} pool"
                )

    def test_to_dict_has_required_keys(self):
        """SentenceRecord.to_dict() must include all traceability fields."""
        required_keys = {
            "sentence_id", "review_id", "source_row_index",
            "sentence_text", "start", "end",
            "label", "confidence", "is_provisional", "classifier_note",
        }
        all_sents, _ = classify_and_route_review("REV-DICT", 0, _REVIEW_COMPLAINT)
        for rec in all_sents:
            d = rec.to_dict()
            for key in required_keys:
                self.assertIn(key, d, f"Missing key '{key}' in SentenceRecord.to_dict()")

    def test_corpus_routing_pool_sizes(self):
        """classify_and_route_corpus must aggregate pools correctly."""
        review_ids = ["REV-A", "REV-B", "REV-C"]
        indices = [0, 1, 2]
        texts = [_REVIEW_COMPLAINT, _REVIEW_RECOMMENDATION, _REVIEW_PRAISE]

        all_sents, corpus_pools = classify_and_route_corpus(review_ids, indices, texts)
        total_pooled = corpus_pools.total
        self.assertEqual(total_pooled, len(all_sents))
        self.assertGreater(total_pooled, 0)

    def test_corpus_mismatched_lengths_raises(self):
        """Mismatched lengths must raise ValueError."""
        with self.assertRaises(ValueError):
            classify_and_route_corpus(["REV-A", "REV-B"], [0], ["text"])


# =============================================================================
# Group 4: Complaint Clustering (MiniLM embedding + KMeans + c-TF-IDF)
# =============================================================================

class TestComplaintClustering(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Build a complaint sentence pool for clustering tests."""
        reviews = [
            ("REV-CC-000", 0, "However, the pump broke and leaked everywhere. Terrible quality."),
            ("REV-CC-001", 1, "The serum caused burning and redness on my cheeks. Avoid!"),
            ("REV-CC-002", 2, "Unfortunately the bottle cracked during shipping. Very disappointed."),
            ("REV-CC-003", 3, "But the cream jammed in the dispenser and nothing comes out."),
            ("REV-CC-004", 4, "This caused a terrible rash on my neck. Horrible reaction."),
            ("REV-CC-005", 5, "The product arrived damaged and spilled all over the box."),
            ("REV-CC-006", 6, "Although I liked the scent, it caused stinging on my face."),
            ("REV-CC-007", 7, "However the lid cracked and the product leaked in my bag."),
            ("REV-CC-008", 8, "Unfortunately it caused dermatitis after just one application."),
            ("REV-CC-009", 9, "The pump failed immediately, completely useless dispenser."),
            ("REV-CC-010", 10, "But the formula changed and now it causes horrible breakouts."),
            ("REV-CC-011", 11, "The serum leaked and the dropper arrived broken. Refund needed."),
        ]
        all_sents = []
        for rev_id, src_idx, text in reviews:
            sents, _ = classify_and_route_review(rev_id, src_idx, text)
            all_sents.extend(sents)

        cls.complaint_pool = [s for s in all_sents if s.label == LABEL_COMPLAINT]

    def test_has_complaint_sentences(self):
        """At least some sentences must be in the complaint pool."""
        self.assertGreater(
            len(self.complaint_pool), 0,
            "Complaint pool is empty — sentences not classified as COMPLAINT."
        )

    def test_embedding_shape(self):
        """MiniLM embeddings of complaint sentences must be (N, 384)."""
        from app.ml.complaint_clustering import embed_sentences
        texts = [s.sentence_text for s in self.complaint_pool]
        if not texts:
            self.skipTest("No complaint sentences to embed")
        embeddings = embed_sentences(texts, cache_key_suffix="_test")
        self.assertEqual(embeddings.shape[0], len(texts))
        self.assertEqual(embeddings.shape[1], 384,
                         f"Expected 384-dim embeddings, got {embeddings.shape[1]}")

    def test_embeddings_normalized(self):
        """MiniLM output embeddings must be L2-normalized (norm ≈ 1.0)."""
        import numpy as np
        from app.ml.complaint_clustering import embed_sentences
        texts = [s.sentence_text for s in self.complaint_pool[:4]]
        if not texts:
            self.skipTest("No complaint sentences to embed")
        embeddings = embed_sentences(texts, cache_key_suffix="_norm_test")
        norms = np.linalg.norm(embeddings, axis=1)
        for i, n in enumerate(norms):
            self.assertAlmostEqual(n, 1.0, places=4,
                                   msg=f"Embedding {i} not unit-normalized: norm={n:.6f}")

    def test_cluster_result_structure(self):
        """cluster_complaint_sentences must return the expected dict keys."""
        from app.ml.complaint_clustering import cluster_complaint_sentences
        result = cluster_complaint_sentences(self.complaint_pool, n_clusters=3)

        required_top_keys = {
            "clusters", "n_complaint_sentences",
            "n_clusters_actual", "is_provisional", "provisional_notices",
        }
        for key in required_top_keys:
            self.assertIn(key, result, f"Missing top-level key: {key}")

        self.assertEqual(result["n_complaint_sentences"], len(self.complaint_pool))
        self.assertIsInstance(result["clusters"], list)
        self.assertGreater(len(result["clusters"]), 0)

    def test_cluster_verbatims_have_traceability(self):
        """Each verbatim in cluster output must include traceability fields."""
        from app.ml.complaint_clustering import cluster_complaint_sentences
        result = cluster_complaint_sentences(self.complaint_pool, n_clusters=3)
        required_verbatim_keys = {
            "sentence_id", "review_id", "source_row_index",
            "sentence_text", "start", "end",
        }
        for cluster in result["clusters"]:
            for verbatim in cluster["verbatims"]:
                for key in required_verbatim_keys:
                    self.assertIn(key, verbatim, f"Verbatim missing key: {key}")

    def test_ctfidf_keywords_returned(self):
        """Every cluster must have at least 1 c-TF-IDF keyword."""
        from app.ml.complaint_clustering import cluster_complaint_sentences
        result = cluster_complaint_sentences(self.complaint_pool, n_clusters=3)
        for cluster in result["clusters"]:
            self.assertIsInstance(cluster["keywords"], list)
            self.assertGreater(len(cluster["keywords"]), 0,
                               f"Cluster {cluster['cluster_id']} has no keywords")

    def test_empty_pool_returns_empty_result(self):
        """Empty complaint pool must return an empty result without raising."""
        from app.ml.complaint_clustering import cluster_complaint_sentences
        result = cluster_complaint_sentences([], n_clusters=6)
        self.assertEqual(result["clusters"], [])
        self.assertEqual(result["n_complaint_sentences"], 0)
        self.assertTrue(result["is_provisional"])

    def test_cluster_severity_values(self):
        """All cluster severity values must be one of LOW/MEDIUM/HIGH/CRITICAL."""
        from app.ml.complaint_clustering import cluster_complaint_sentences
        result = cluster_complaint_sentences(self.complaint_pool, n_clusters=3)
        valid = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        for cluster in result["clusters"]:
            self.assertIn(cluster["severity"], valid,
                          f"Invalid severity: {cluster['severity']}")

    def test_verbatim_offsets_valid(self):
        """Verbatim start/end offsets must be valid against sentence_text."""
        from app.ml.complaint_clustering import cluster_complaint_sentences
        result = cluster_complaint_sentences(self.complaint_pool, n_clusters=3)
        for cluster in result["clusters"]:
            for verbatim in cluster["verbatims"]:
                text = verbatim["sentence_text"]
                start = verbatim["start"]
                end = verbatim["end"]
                # Offsets are relative to the review, not the sentence itself,
                # so we just check they are non-negative integers
                self.assertIsInstance(start, int)
                self.assertIsInstance(end, int)
                self.assertGreaterEqual(start, 0)
                self.assertGreater(end, start)

    def test_ctfidf_keyword_extraction_standalone(self):
        """extract_ctfidf_keywords must return a dict with cluster_id keys."""
        from app.ml.complaint_clustering import extract_ctfidf_keywords
        cluster_texts = {
            0: ["pump broke leaked everywhere", "dispenser jammed useless"],
            1: ["burning redness rash skin", "dermatitis allergic reaction"],
        }
        keywords = extract_ctfidf_keywords(cluster_texts, top_n=5)
        self.assertEqual(set(keywords.keys()), {0, 1})
        for cid, kws in keywords.items():
            self.assertIsInstance(kws, list)
            self.assertLessEqual(len(kws), 5)

    def test_cluster_medoid_and_title(self):
        """Every cluster must have a descriptive defect title and medoid_verbatim."""
        from app.ml.complaint_clustering import cluster_complaint_sentences
        result = cluster_complaint_sentences(self.complaint_pool, n_clusters=3)
        for cluster in result["clusters"]:
            self.assertIn("title", cluster)
            self.assertIsInstance(cluster["title"], str)
            self.assertGreater(len(cluster["title"].strip()), 0)
            self.assertIn("medoid_verbatim", cluster)
            self.assertIsInstance(cluster["medoid_verbatim"], str)
            self.assertGreater(len(cluster["medoid_verbatim"].strip()), 0)
            # The medoid must be the very first verbatim
            self.assertEqual(cluster["verbatims"][0]["sentence_text"], cluster["medoid_verbatim"])

    def test_praise_clustering_structure(self):
        """cluster_praise_sentences must return strength drivers, delight metrics, and traceable verbatims."""
        from app.ml.complaint_clustering import cluster_praise_sentences
        # Create synthetic praise sentences
        praise_reviews = [
            ("REV-PR-001", 1, "This is my holy grail moisturizer, incredibly hydrating and gentle."),
            ("REV-PR-002", 2, "I love how it cleared my skin and gave me an amazing glowing texture."),
            ("REV-PR-003", 3, "Absorbs instantly without any grease, absolutely fantastic formula."),
            ("REV-PR-004", 4, "My favorite skincare purchase ever, leaves skin so smooth and soft."),
            ("REV-PR-005", 5, "Works wonders for dry skin, truly the best cream I have used."),
        ]
        praise_sents = []
        for rev_id, src_idx, text in praise_reviews:
            recs, pools = classify_and_route_review(rev_id, src_idx, text)
            praise_sents.extend(pools.praise)

        result = cluster_praise_sentences(praise_sents, n_clusters=2)
        self.assertIn("praise_clusters", result)
        self.assertIn("clusters", result)
        self.assertGreaterEqual(result["n_clusters_actual"], 1)

        for cluster in result["clusters"]:
            self.assertIn("title", cluster)
            self.assertIn("strength_drivers", cluster)
            self.assertIn("delight_score", cluster)
            self.assertIn("medoid_verbatim", cluster)
            self.assertIn("verbatims", cluster)
            self.assertGreater(len(cluster["verbatims"]), 0)
            self.assertIn("start", cluster["verbatims"][0])
            self.assertIn("end", cluster["verbatims"][0])

        # Empty pool edge case
        empty_res = cluster_praise_sentences([])
        self.assertEqual(empty_res["n_clusters_actual"], 0)
        self.assertEqual(empty_res["clusters"], [])



# =============================================================================
# Group 5: Real-data smoke tests on cosmetics_10k.csv
# =============================================================================

class TestSentencePipelineOnRealData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        dataset_path = DATASETS["cosmetics_10k"]
        if not dataset_path.exists():
            raise unittest.SkipTest(f"Real dataset not found: {dataset_path}")
        df = pd.read_csv(dataset_path)
        cls.sample = df["review_text"].dropna().astype(str).head(200).tolist()
        cls.review_ids = [f"REV-REAL-{i:05d}" for i in range(len(cls.sample))]
        cls.source_indices = list(range(len(cls.sample)))

    def test_sentence_extraction_offset_invariant_on_real_data(self):
        """For every sentence from a real review, text[start:end] == sentence_text."""
        n_checked = 0
        for i, (rev_id, text) in enumerate(zip(self.review_ids, self.sample)):
            for sent_text, start, end in deconstruct_sentences(rev_id, i, text):
                self.assertEqual(
                    text[start:end], sent_text,
                    f"Offset invariant failed for review {rev_id}"
                )
                n_checked += 1
        self.assertGreater(n_checked, 0, "No sentences extracted from real data")

    def test_all_sentences_have_valid_labels(self):
        """All sentences from real reviews must have a valid label."""
        valid = {LABEL_COMPLAINT, LABEL_RECOMMENDATION, LABEL_PRAISE, LABEL_NOISE, LABEL_PRAISE_NOISE}
        all_sents, _ = classify_and_route_corpus(
            self.review_ids, self.source_indices, self.sample
        )
        for rec in all_sents:
            self.assertIn(rec.label, valid,
                          f"Invalid label: {rec.label}")

    def test_all_sentences_routed_exactly_once_real_data(self):
        """All sentences must appear in exactly one pool (no duplicates/gaps)."""
        all_sents, pools = classify_and_route_corpus(
            self.review_ids, self.source_indices, self.sample
        )
        pooled = set(
            s.sentence_id for s in
            pools.complaint + pools.recommendation + pools.praise_noise
        )
        all_ids = set(s.sentence_id for s in all_sents)
        self.assertEqual(pooled, all_ids)
        self.assertEqual(
            len(pools.complaint) + len(pools.recommendation) + len(pools.praise_noise),
            len(all_sents)
        )

    def test_complaint_pool_not_empty_on_real_reviews(self):
        """The cosmetics dataset is known to contain complaint sentences."""
        all_sents, pools = classify_and_route_corpus(
            self.review_ids, self.source_indices, self.sample
        )
        self.assertGreater(
            len(pools.complaint), 0,
            "COMPLAINT pool is empty on real reviews — heuristic may be broken"
        )

    def test_sentence_pipeline_latency_real_data(self):
        """Sentence pipeline must process 200 real reviews in < 5 seconds."""
        t0 = time.time()
        classify_and_route_corpus(
            self.review_ids, self.source_indices, self.sample
        )
        elapsed = time.time() - t0
        self.assertLess(elapsed, 5.0,
                        f"Sentence pipeline took {elapsed:.2f}s for 200 reviews (threshold: 5s)")


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
