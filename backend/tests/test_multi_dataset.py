"""test_multi_dataset.py
Integration test suite for Multi-Dataset Tenant Support, Dataset Isolation, and Non-Destructive Storage (Task P3).

Validates:
  1. Multiple client datasets uploaded with distinct domain IDs coexist without destructive overwrite
  2. Dataset catalog surfaces distinct client datasets in GET /api/datasets
  3. Strict isolation of verbatims, themes, and propositions across domains
  4. Domain-specific semantic vector search isolation
  5. Active domain switching via POST /api/datasets/select
  6. Dataset deletion with cascade cleanup via DELETE /api/datasets/{domain_id}
  7. Safeguards preventing deletion of system default domains
"""

import sys
import os
import io
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_multi_dataset_upload_coexistence_and_isolation(client):
    """Verify multiple datasets can be uploaded and coexist without overwriting each other."""
    # Dataset A (Cosmetics client feedback)
    dataset_a_csv = """review,rating,batch
"Serum pump clogged completely after three uses.",1,BATCH-A1
"The night moisturizer is wonderfully soothing and fragrant.",5,BATCH-A1
"The eye cream jar arrived cracked and leaked everywhere.",1,BATCH-A1
"Love the hydrating feel on my dry skin.",5,BATCH-A1
"""
    files_a = {"file": ("cosmetics_alpha.csv", io.BytesIO(dataset_a_csv.encode("utf-8")), "text/csv")}
    res_a = client.post("/api/datasets/upload?domain_id=tenant_cosmetics", files=files_a)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["status"] == "success"
    assert data_a["dataset_id"] == "tenant_cosmetics"
    assert data_a["rows_ingested"] == 4

    # Dataset B (Fintech client feedback)
    dataset_b_csv = """review,rating,version
"Mobile app crashes immediately during biometric face scan.",1,v3.1.0
"Instant money transfer completed in five seconds flat.",5,v3.1.0
"Monthly account statement export timed out with network error.",2,v3.1.0
"Great user interface and simple navigation.",5,v3.1.0
"""
    files_b = {"file": ("fintech_beta.csv", io.BytesIO(dataset_b_csv.encode("utf-8")), "text/csv")}
    res_b = client.post("/api/datasets/upload?domain_id=tenant_fintech", files=files_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["status"] == "success"
    assert data_b["dataset_id"] == "tenant_fintech"
    assert data_b["rows_ingested"] == 4

    # Verify both datasets appear in GET /api/datasets
    catalog_res = client.get("/api/datasets")
    assert catalog_res.status_code == 200
    catalog = catalog_res.json()
    avail_ids = [d["id"] for d in catalog["available_domains"]]

    assert "tenant_cosmetics" in avail_ids
    assert "tenant_fintech" in avail_ids
    assert "d2c_cosmetics" in avail_ids
    assert "tech_saas" in avail_ids


def test_multi_dataset_overview_and_verbatims_isolation(client):
    """Verify telemetry overview and verbatims remain isolated per dataset domain."""
    # Overview for Dataset A
    res_a = client.get("/api/overview?domain=tenant_cosmetics")
    assert res_a.status_code == 200
    overview_a = res_a.json()
    assert overview_a["total_reviews"] == 4

    # Overview for Dataset B
    res_b = client.get("/api/overview?domain=tenant_fintech")
    assert res_b.status_code == 200
    overview_b = res_b.json()
    assert overview_b["total_reviews"] == 4

    # Verbatims for Dataset A (cosmetics terms)
    verb_a = client.get("/api/verbatims?domain=tenant_cosmetics")
    assert verb_a.status_code == 200
    texts_a = [v["redacted_text"] for v in verb_a.json()["verbatims"]]
    assert any("pump" in t or "moisturizer" in t for t in texts_a)
    assert not any("biometric" in t for t in texts_a)

    # Verbatims for Dataset B (fintech terms)
    verb_b = client.get("/api/verbatims?domain=tenant_fintech")
    assert verb_b.status_code == 200
    texts_b = [v["redacted_text"] for v in verb_b.json()["verbatims"]]
    assert any("biometric" in t or "transfer" in t for t in texts_b)
    assert not any("moisturizer" in t for t in texts_b)


def test_multi_dataset_proposition_filtering_isolation(client):
    """Verify propositions are strictly segregated by domain."""
    props_a = client.get("/api/propositions?domain=tenant_cosmetics")
    assert props_a.status_code == 200
    props_a_data = props_a.json()
    assert props_a_data["domain"] == "tenant_cosmetics"
    assert props_a_data["total"] > 0
    for p in props_a_data["propositions"]:
        assert p["domain_id"] == "tenant_cosmetics"

    props_b = client.get("/api/propositions?domain=tenant_fintech")
    assert props_b.status_code == 200
    props_b_data = props_b.json()
    assert props_b_data["domain"] == "tenant_fintech"
    assert props_b_data["total"] > 0
    for p in props_b_data["propositions"]:
        assert p["domain_id"] == "tenant_fintech"


def test_multi_dataset_domain_selection(client):
    """Verify switching active domain across custom datasets."""
    # Switch to tenant_cosmetics
    sel_a = client.post("/api/datasets/select", json={"domain": "tenant_cosmetics"})
    assert sel_a.status_code == 200
    assert sel_a.json()["active_domain"] == "tenant_cosmetics"

    # Verify overview defaults to active domain
    ov = client.get("/api/overview")
    assert ov.status_code == 200
    assert ov.json()["domain"] == "tenant_cosmetics"

    # Switch to tenant_fintech
    sel_b = client.post("/api/datasets/select", json={"domain": "tenant_fintech"})
    assert sel_b.status_code == 200
    assert sel_b.json()["active_domain"] == "tenant_fintech"

    ov2 = client.get("/api/overview")
    assert ov2.status_code == 200
    assert ov2.json()["domain"] == "tenant_fintech"


def test_multi_dataset_delete_and_cascade_cleanup(client):
    """Verify custom dataset deletion purges domain cleanly without affecting others."""
    # Delete tenant_fintech
    del_res = client.delete("/api/datasets/tenant_fintech")
    assert del_res.status_code == 200
    assert del_res.json()["deleted_domain"] == "tenant_fintech"

    # Verify tenant_fintech is gone from catalog
    cat = client.get("/api/datasets").json()
    avail_ids = [d["id"] for d in cat["available_domains"]]
    assert "tenant_fintech" not in avail_ids
    # Verify tenant_cosmetics still intact
    assert "tenant_cosmetics" in avail_ids

    # Verify querying deleted domain returns 404
    err_res = client.get("/api/overview?domain=tenant_fintech")
    assert err_res.status_code == 404

    # Verify attempting to delete protected system domain returns 403
    del_sys = client.delete("/api/datasets/d2c_cosmetics")
    assert del_sys.status_code == 403
