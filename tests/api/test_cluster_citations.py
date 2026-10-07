import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_complaint_cluster_citations_initial_and_incremental():
    # 1. Fetch cluster list
    resp = client.get("/api/complaint-clusters?domain=d2c_cosmetics")
    assert resp.status_code == 200
    clusters = resp.json()["clusters"]
    assert len(clusters) > 0
    cid = clusters[0]["cluster_id"]
    cluster_sentence_count = clusters[0]["sentence_count"]
    assert cluster_sentence_count > 10

    # 2. Initial fetch: 10 citations
    r1 = client.get(f"/api/complaint-clusters/{cid}/verbatims?offset=0&limit=10&domain=d2c_cosmetics")
    assert r1.status_code == 200
    d1 = r1.json()
    assert len(d1["verbatims"]) == 10
    assert d1["total"] == cluster_sentence_count
    assert d1["has_more"] is True
    first_ids = {v["sentence_id"] for v in d1["verbatims"]}

    # 3. Next scroll fetch: 20 citations
    r2 = client.get(f"/api/complaint-clusters/{cid}/verbatims?offset=10&limit=20&domain=d2c_cosmetics")
    assert r2.status_code == 200
    d2 = r2.json()
    assert len(d2["verbatims"]) == min(20, cluster_sentence_count - 10)
    second_ids = {v["sentence_id"] for v in d2["verbatims"]}
    # Verify no duplicate overlap between page 1 and page 2
    assert len(first_ids.intersection(second_ids)) == 0


def test_complaint_cluster_citations_search_filter():
    resp = client.get("/api/complaint-clusters?domain=d2c_cosmetics")
    clusters = resp.json()["clusters"]
    cid = clusters[0]["cluster_id"]

    # Initial fetch to get a word from the first citation
    r1 = client.get(f"/api/complaint-clusters/{cid}/verbatims?offset=0&limit=5&domain=d2c_cosmetics")
    text = r1.json()["verbatims"][0]["sentence_text"]
    words = [w for w in text.split() if len(w) > 4]
    search_term = words[0] if words else "skin"

    # Filter by search term
    r_search = client.get(f"/api/complaint-clusters/{cid}/verbatims?offset=0&limit=10&search={search_term}&domain=d2c_cosmetics")
    assert r_search.status_code == 200
    d_search = r_search.json()
    for item in d_search["verbatims"]:
        assert search_term.lower() in item["sentence_text"].lower() or search_term.lower() in item["review_id"].lower()


def test_tech_saas_complaint_citations():
    resp = client.get("/api/complaint-clusters?domain=tech_saas")
    assert resp.status_code == 200
    clusters = resp.json()["clusters"]
    assert len(clusters) > 0
    cid = clusters[0]["cluster_id"]
    total_count = clusters[0]["sentence_count"]

    r = client.get(f"/api/complaint-clusters/{cid}/verbatims?offset=0&limit=10&domain=tech_saas")
    assert r.status_code == 200
    data = r.json()
    assert len(data["verbatims"]) == 10
    assert data["total"] == total_count
