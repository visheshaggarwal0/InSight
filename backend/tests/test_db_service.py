"""test_db_service.py
Unit and integration test suite for Proposition SQL Database Persistence & Migration.

Validates:
  1. PropositionModel schema fields, pgvector embedding, and serialization
  2. DatabaseService.seed_domain storing atomic 4-way propositions
  3. Filtered retrieval by 4-way intent, operational severity, and actionability
  4. Per-review proposition retrieval ordered by sentence index
  5. 4-Way intent aggregation counts (COMPLAINT, RECOMMENDATION, PRAISE, NOISE)
  6. Proposition-level semantic vector search with intent filtering
  7. Idempotent domain overwrite and cascade cleanup
  8. REST API endpoints GET /api/propositions and POST /api/search/propositions
"""

import sys
import os
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.core.database import SessionLocal, init_db
from app.models.schema import DomainModel, ReviewModel, PropositionModel
from app.services.db_service import db_service
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_proposition_model_fields_and_dict():
    """Verify PropositionModel schema contract and serialization."""
    dummy_emb = [0.05] * 384
    prop = PropositionModel(
        id="REV-TEST-001::P000",
        review_id="REV-TEST-001",
        domain_id="test_domain",
        sentence_idx=0,
        text="The serum bottle pump jammed and broke immediately.",
        char_start=0,
        char_end=52,
        intent="COMPLAINT",
        severity="P1",
        confidence=0.92,
        is_actionable=1,
        embedding=dummy_emb,
        detected_marker="jammed",
        extra_metadata={"source_row_index": 0},
    )

    d = prop.to_dict(include_embedding=True)
    assert d["id"] == "REV-TEST-001::P000"
    assert d["proposition_id"] == "REV-TEST-001::P000"
    assert d["review_id"] == "REV-TEST-001"
    assert d["domain_id"] == "test_domain"
    assert d["sentence_idx"] == 0
    assert d["text"] == "The serum bottle pump jammed and broke immediately."
    assert d["char_start"] == 0
    assert d["char_end"] == 52
    assert d["intent"] == "COMPLAINT"
    assert d["classification"] == "COMPLAINT"
    assert d["severity"] == "P1"
    assert d["confidence"] == 0.92
    assert d["is_actionable"] is True
    assert d["detected_marker"] == "jammed"
    assert d["extra_metadata"] == {"source_row_index": 0}
    assert len(d["embedding"]) == 384


def test_seed_domain_persists_propositions(db_session):
    """Verify DatabaseService.seed_domain saves first-class propositions."""
    domain_id = "test_persistence_domain"

    # Create dummy embeddings of unit length
    v1 = np.random.randn(384).astype(np.float32)
    v1 /= np.linalg.norm(v1)
    v2 = np.random.randn(384).astype(np.float32)
    v2 /= np.linalg.norm(v2)

    sample_reviews = [
        {
            "id": "REV-PERSIST-001",
            "redacted_text": "I love the soothing lavender aroma! But the plastic nozzle broke on day two.",
            "rating": 2,
            "propositions": [
                {
                    "proposition_id": "REV-PERSIST-001::P000",
                    "sentence_idx": 0,
                    "text": "I love the soothing lavender aroma!",
                    "char_start": 0,
                    "char_end": 35,
                    "intent": "PRAISE",
                    "severity": "P3",
                    "confidence": 0.88,
                    "is_actionable": True,
                    "embedding": v1.tolist(),
                },
                {
                    "proposition_id": "REV-PERSIST-001::P001",
                    "sentence_idx": 1,
                    "text": "But the plastic nozzle broke on day two.",
                    "char_start": 36,
                    "char_end": 76,
                    "intent": "COMPLAINT",
                    "severity": "P1",
                    "confidence": 0.94,
                    "is_actionable": True,
                    "embedding": v2.tolist(),
                },
            ],
        },
        {
            "id": "REV-PERSIST-002",
            "redacted_text": "Please offer a 100ml refill pouch option. Order arrived on Tuesday.",
            "rating": 4,
            "propositions": [
                {
                    "proposition_id": "REV-PERSIST-002::P000",
                    "sentence_idx": 0,
                    "text": "Please offer a 100ml refill pouch option.",
                    "char_start": 0,
                    "char_end": 41,
                    "intent": "RECOMMENDATION",
                    "severity": "P3",
                    "confidence": 0.85,
                    "is_actionable": True,
                    "embedding": v1.tolist(),
                },
                {
                    "proposition_id": "REV-PERSIST-002::P001",
                    "sentence_idx": 1,
                    "text": "Order arrived on Tuesday.",
                    "char_start": 42,
                    "char_end": 67,
                    "intent": "NOISE",
                    "severity": "P3",
                    "confidence": 0.50,
                    "is_actionable": False,
                    "embedding": None,
                },
            ],
        },
    ]

    domain_info = {
        "id": domain_id,
        "name": "Test Persistence Domain",
        "category": "Testing",
        "focus": "Testing Proposition Persistence",
    }

    success = db_service.seed_domain(
        db=db_session,
        domain_info=domain_info,
        reviews=sample_reviews,
        themes=[],
        drift_results={},
        eval_results={},
        overwrite=True,
    )
    assert success is True

    # Check reviews and propositions in DB
    db_reviews = db_session.query(ReviewModel).filter(ReviewModel.domain_id == domain_id).all()
    assert len(db_reviews) == 2

    db_props = db_session.query(PropositionModel).filter(PropositionModel.domain_id == domain_id).all()
    assert len(db_props) == 4


def test_get_propositions_filtering_and_pagination(db_session):
    """Verify get_propositions filtering by 4-way intent and actionability."""
    domain_id = "test_persistence_domain"

    # All propositions
    all_res = db_service.get_propositions(db_session, domain_id=domain_id)
    assert all_res["total"] == 4
    assert len(all_res["propositions"]) == 4

    # Intent = COMPLAINT
    complaints = db_service.get_propositions(db_session, domain_id=domain_id, intent="COMPLAINT")
    assert complaints["total"] == 1
    assert complaints["propositions"][0]["intent"] == "COMPLAINT"
    assert complaints["propositions"][0]["severity"] == "P1"

    # Intent = PRAISE
    praise = db_service.get_propositions(db_session, domain_id=domain_id, intent="PRAISE")
    assert praise["total"] == 1
    assert praise["propositions"][0]["intent"] == "PRAISE"

    # Intent = RECOMMENDATION
    recommendations = db_service.get_propositions(db_session, domain_id=domain_id, intent="RECOMMENDATION")
    assert recommendations["total"] == 1
    assert recommendations["propositions"][0]["intent"] == "RECOMMENDATION"

    # Intent = NOISE
    noise = db_service.get_propositions(db_session, domain_id=domain_id, intent="NOISE")
    assert noise["total"] == 1
    assert noise["propositions"][0]["intent"] == "NOISE"

    # Actionable filtering
    act_true = db_service.get_propositions(db_session, domain_id=domain_id, is_actionable=True)
    assert act_true["total"] == 3

    act_false = db_service.get_propositions(db_session, domain_id=domain_id, is_actionable=False)
    assert act_false["total"] == 1

    # Pagination
    page_1 = db_service.get_propositions(db_session, domain_id=domain_id, limit=2, offset=0)
    assert len(page_1["propositions"]) == 2
    assert page_1["limit"] == 2
    assert page_1["offset"] == 0


def test_get_propositions_by_review(db_session):
    """Verify per-review proposition retrieval maintains sentence index order."""
    props = db_service.get_propositions_by_review(db_session, review_id="REV-PERSIST-001")
    assert len(props) == 2
    assert props[0]["sentence_idx"] == 0
    assert props[0]["intent"] == "PRAISE"
    assert props[1]["sentence_idx"] == 1
    assert props[1]["intent"] == "COMPLAINT"


def test_count_propositions_by_intent(db_session):
    """Verify 4-way aggregation counts."""
    domain_id = "test_persistence_domain"
    counts = db_service.count_propositions_by_intent(db_session, domain_id=domain_id)

    assert counts["COMPLAINT"] == 1
    assert counts["RECOMMENDATION"] == 1
    assert counts["PRAISE"] == 1
    assert counts["NOISE"] == 1
    assert counts["actionable"] == 3
    assert counts["total"] == 4


def test_search_propositions_semantic(db_session):
    """Verify proposition-level semantic vector search with intent filtering."""
    domain_id = "test_persistence_domain"

    # Query using the complaint proposition vector
    comp_prop = db_session.query(PropositionModel).filter(
        PropositionModel.domain_id == domain_id,
        PropositionModel.intent == "COMPLAINT"
    ).first()
    assert comp_prop is not None

    query_vec = comp_prop.embedding
    results = db_service.search_propositions_semantic(
        db=db_session,
        query_vector=query_vec,
        domain_id=domain_id,
        limit=5,
    )
    assert len(results) >= 1
    top = results[0]
    assert top["similarity_score"] >= 0.99  # Self-similarity
    assert top["id"] == comp_prop.id

    # Filter by intent = PRAISE
    praise_results = db_service.search_propositions_semantic(
        db=db_session,
        query_vector=query_vec,
        domain_id=domain_id,
        intent="PRAISE",
        limit=5,
    )
    assert len(praise_results) >= 1
    assert all(r["intent"] == "PRAISE" for r in praise_results)


def test_seed_domain_overwrite_cleans_propositions(db_session):
    """Verify domain overwrite wipes old propositions idempotently."""
    domain_id = "test_persistence_domain"

    # Re-seed with a single review
    sample_reviews = [
        {
            "id": "REV-NEW-001",
            "redacted_text": "Great face wash.",
            "rating": 5,
            "propositions": [
                {
                    "proposition_id": "REV-NEW-001::P000",
                    "sentence_idx": 0,
                    "text": "Great face wash.",
                    "char_start": 0,
                    "char_end": 16,
                    "intent": "PRAISE",
                    "severity": "P3",
                    "confidence": 0.90,
                    "is_actionable": True,
                }
            ],
        }
    ]

    domain_info = {
        "id": domain_id,
        "name": "Test Persistence Domain",
        "category": "Testing",
    }

    db_service.seed_domain(
        db=db_session,
        domain_info=domain_info,
        reviews=sample_reviews,
        themes=[],
        drift_results={},
        eval_results={},
        overwrite=True,
    )

    counts = db_service.count_propositions_by_intent(db_session, domain_id=domain_id)
    assert counts["total"] == 1
    assert counts["PRAISE"] == 1
    assert counts["COMPLAINT"] == 0


def test_api_propositions_endpoints(client):
    """Verify GET /api/propositions and POST /api/search/propositions."""
    # List propositions
    resp = client.get("/api/propositions?domain=test_persistence_domain")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "propositions" in data

    # Search propositions endpoint
    search_resp = client.post(
        "/api/search/propositions",
        json={
            "query": "face wash",
            "domain": "test_persistence_domain",
            "intent": "PRAISE",
            "limit": 5,
        },
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["domain"] == "test_persistence_domain"
    assert search_data["intent_filter"] == "PRAISE"
    assert "results" in search_data
