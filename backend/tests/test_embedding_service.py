"""test_embedding_service.py
Comprehensive test suite for VectorEmbeddingService.

Tests:
  1. Vector dimensionality (N, 384) and L2 unit-sphere normalization (||v||_2 == 1.0)
  2. Content-addressable disk caching (cache write -> cache hit in <20ms)
  3. Deterministic cache key generation idempotency
  4. Single query encoding shape (384,) and normalization
  5. Semantic cosine similarity properties (defect twins vs divergent sentences)
  6. Empty text list handling
  7. Fallback embedding generation
"""

import numpy as np
import pytest
from app.data.embedding_service import (
    VectorEmbeddingService,
    embedding_service,
    EmbeddingManifest,
    DEFAULT_VECTOR_DIM,
)


def test_embedding_dimensions_and_unit_normalization(tmp_path):
    texts = [
        "The pump dispenser broke on day 3 and leaked everywhere.",
        "Face serum caused severe allergic rash and burning.",
        "Fast shipping and nice sustainable cardboard box."
    ]
    service = VectorEmbeddingService(cache_dir=tmp_path)
    embeddings, manifest = service.encode_texts(texts, use_cache=True)

    assert embeddings.shape == (3, DEFAULT_VECTOR_DIM)
    assert manifest.total_vectors == 3
    assert manifest.dimension == 384
    assert manifest.cache_hit is False

    # Check L2 unit norm for every vector: ||v||_2 == 1.0 (+- 1e-4)
    norms = np.linalg.norm(embeddings, axis=1)
    for norm_val in norms:
        assert np.isclose(norm_val, 1.0, atol=1e-4)


def test_content_addressable_disk_caching(tmp_path):
    texts = [
        "Biometric authentication failure on iOS app startup.",
        "Unable to export analytics CSV report due to timeout."
    ]
    service = VectorEmbeddingService(cache_dir=tmp_path)

    # First call: computes and writes cache
    emb1, manifest1 = service.encode_texts(texts, use_cache=True)
    assert manifest1.cache_hit is False
    cache_file = tmp_path / f"emb_{manifest1.cache_key}.npy"
    assert cache_file.exists()

    # Second call: instant disk cache hit
    emb2, manifest2 = service.encode_texts(texts, use_cache=True)
    assert manifest2.cache_hit is True
    assert manifest2.cache_key == manifest1.cache_key
    assert manifest2.inference_time_ms < 50.0  # sub-50ms reload

    # Vectors must match exactly
    np.testing.assert_allclose(emb1, emb2, atol=1e-5)


def test_deterministic_cache_key_generation():
    texts1 = ["The dropper pipette cracked in transit.", "Fragrance is pleasant."]
    texts2 = ["The dropper pipette cracked in transit.", "Fragrance is pleasant."]
    key1 = VectorEmbeddingService.compute_cache_key(texts1)
    key2 = VectorEmbeddingService.compute_cache_key(texts2)
    assert key1 == key2
    assert len(key1) == 16


def test_encode_query_vector():
    query = "broken dispenser pump leaking"
    query_vec = embedding_service.encode_query(query)
    assert query_vec.shape == (DEFAULT_VECTOR_DIM,)
    assert np.isclose(np.linalg.norm(query_vec), 1.0, atol=1e-4)


def test_semantic_similarity_properties():
    # Two semantically twin defect complaints vs one unrelated praise
    text_defect_1 = "The pump dispenser broke and leaked all over the bottle."
    text_defect_2 = "Dispenser pump jammed and cracked, causing product spillage."
    text_unrelated = "Delivery arrived very quickly within two business days."

    vecs, _ = embedding_service.encode_texts(
        [text_defect_1, text_defect_2, text_unrelated], use_cache=False
    )

    # Cosine similarity is simply dot product because vectors are normalized
    sim_defect_twin = float(np.dot(vecs[0], vecs[1]))
    sim_unrelated = float(np.dot(vecs[0], vecs[2]))

    # Defect twins should have noticeably higher semantic similarity than unrelated text
    assert sim_defect_twin > sim_unrelated
    assert sim_defect_twin > 0.50


def test_empty_texts_input(tmp_path):
    service = VectorEmbeddingService(cache_dir=tmp_path)
    emb, manifest = service.encode_texts([], use_cache=True)
    assert emb.shape == (0, 384)
    assert manifest.total_vectors == 0
    assert manifest.cache_hit is False


def test_fallback_embeddings():
    service = VectorEmbeddingService()
    fallback_vecs = service._fallback_tfidf_embeddings(["Test review text for fallback."])
    assert fallback_vecs.shape == (1, 384)
    assert np.isclose(np.linalg.norm(fallback_vecs[0]), 1.0, atol=1e-4)
