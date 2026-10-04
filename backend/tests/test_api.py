import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_and_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data
    assert data["database"]["connected"] is True
    assert "pgvector_version" in data["database"]

def test_db_status_endpoint(client):
    response = client.get("/api/db/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    if data.get("dialect") == "postgresql":
        assert data["reviews_count"] >= 20000
        assert data["themes_count"] >= 12
        assert data["domains_count"] >= 2
    else:
        assert "reviews_count" in data

def test_overview_endpoint(client):
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_reviews" in data
    assert "sentiment_counts" in data
    assert "critical_themes_count" in data
    assert data["total_reviews"] > 0
    assert "NEGATIVE" in data["sentiment_counts"]

def test_themes_endpoint(client):
    response = client.get("/api/themes")
    assert response.status_code == 200
    data = response.json()
    assert "themes" in data
    themes = data["themes"]
    assert isinstance(themes, list)
    assert len(themes) > 0
    first_theme = themes[0]
    assert "title" in first_theme
    assert "severity" in first_theme
    assert "keywords" in first_theme
    assert len(first_theme["keywords"]) > 0

def test_verbatims_endpoint(client):
    response = client.get("/api/verbatims?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "verbatims" in data
    verbatims = data["verbatims"]
    assert isinstance(verbatims, list)
    assert len(verbatims) == 10
    rev = verbatims[0]
    assert "sentiment_pred" in rev
    assert "sentiment_confidence" in rev

def test_datasets_endpoint(client):
    response = client.get("/api/datasets")
    assert response.status_code == 200
    data = response.json()
    assert "active_domain" in data
    assert "available_domains" in data

def test_governance_endpoint(client):
    response = client.get("/api/governance")
    assert response.status_code == 200
    data = response.json()
    assert "evaluation" in data
    eval_data = data["evaluation"]
    assert "accuracy" in eval_data
    assert "macro_f1" in eval_data

def test_ticket_generate_and_persist(client):
    # Call generate ticket for cluster 0
    response = client.post("/api/ticket/generate", json={"cluster_id": 0})
    assert response.status_code == 200
    data = response.json()
    assert "ticket_id" in data
    assert "ticket_markdown" in data
    assert "severity" in data

    # Verify ticket was stored in database
    tickets_resp = client.get("/api/tickets")
    assert tickets_resp.status_code == 200
    t_data = tickets_resp.json()
    assert "tickets" in t_data
    assert len(t_data["tickets"]) > 0

def test_semantic_search_vector(client):
    response = client.post("/api/search/semantic", json={
        "query": "pump dispenser jammed broken packaging",
        "domain": "d2c_cosmetics",
        "limit": 5
    })
    assert response.status_code == 200
    data = response.json()
    assert data["total_matches"] > 0
    assert len(data["results"]) > 0
    top_result = data["results"][0]
    assert "similarity_score" in top_result
    assert "redacted_text" in top_result
    assert top_result["similarity_score"] > 0.0

def test_domain_switch_and_sentiment_stability(client):
    """Verifies seamless switching between domains with different feature spaces without shape mismatch."""
    # Switch to tech_saas
    r1 = client.post("/api/datasets/select", json={"domain": "tech_saas"})
    assert r1.status_code == 200
    assert r1.json()["active_domain"] == "tech_saas"

    # Query overview & verbatims for tech_saas
    saas_ov = client.get("/api/overview")
    assert saas_ov.status_code == 200
    saas_verb = client.get("/api/verbatims?page=1&page_size=5")
    assert saas_verb.status_code == 200

    # Switch back to d2c_cosmetics
    r2 = client.post("/api/datasets/select", json={"domain": "d2c_cosmetics"})
    assert r2.status_code == 200
    assert r2.json()["active_domain"] == "d2c_cosmetics"

    # Query overview & verbatims for d2c_cosmetics
    d2c_ov = client.get("/api/overview")
    assert d2c_ov.status_code == 200
    d2c_verb = client.get("/api/verbatims?page=1&page_size=5")
    assert d2c_verb.status_code == 200

def test_custom_csv_upload(client):
    """Verifies that uploading a custom CSV ingests reviews without crashing even with small sample sizes."""
    csv_payload = b"review_text,rating\nGreat moisturizer,5\nPump broke immediately,1\nNeutral feedback,3"
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("test_upload.csv", csv_payload, "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["rows_ingested"] == 3
    assert data["active_domain"] == "custom"

    # Restore d2c_cosmetics active domain
    client.post("/api/datasets/select", json={"domain": "d2c_cosmetics"})

def test_overview_intent_breakdown(client):
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert "intent_breakdown" in data
    ib = data["intent_breakdown"]
    assert "total_sentences" in ib
    assert "complaints" in ib
    assert "praise" in ib
    assert "recommendations" in ib
    assert "noise" in ib
    assert "actionable_count" in ib
    assert "actionable_rate_pct" in ib

def test_complaint_and_praise_clusters_endpoints(client):
    # Test complaint clusters
    resp_cc = client.get("/api/complaint-clusters")
    assert resp_cc.status_code == 200
    cc_data = resp_cc.json()
    assert "clusters" in cc_data
    assert "total" in cc_data

    # Test feature requests
    resp_fr = client.get("/api/feature-requests")
    assert resp_fr.status_code == 200
    fr_data = resp_fr.json()
    assert "feature_requests" in fr_data

    # Test praise clusters
    resp_pc = client.get("/api/praise-clusters")
    assert resp_pc.status_code == 200
    pc_data = resp_pc.json()
    assert "clusters" in pc_data
    assert "total" in pc_data

