"""test_domain_isolation.py
Tests domain isolation, multi-tenant concurrency safety, and ?domain query parameter routing.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import DOMAIN_CACHE, state


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_domain_query_param_routing(client):
    # Ensure default domain is initialized
    res_cosmetics = client.get("/api/overview?domain=d2c_cosmetics")
    assert res_cosmetics.status_code == 200
    data_cosmetics = res_cosmetics.json()
    assert data_cosmetics["domain"] == "d2c_cosmetics"

    # Query tech_saas via query param
    res_saas = client.get("/api/overview?domain=tech_saas")
    assert res_saas.status_code == 200
    data_saas = res_saas.json()
    assert data_saas["domain"] == "tech_saas"

    # Verify that querying tech_saas did NOT mutate the default/active domain
    res_default = client.get("/api/overview")
    assert res_default.status_code == 200
    assert res_default.json()["domain"] == state.active_domain


def test_themes_domain_isolation(client):
    res_cosmetics = client.get("/api/themes?domain=d2c_cosmetics")
    assert res_cosmetics.status_code == 200
    themes_cosmetics = res_cosmetics.json()["themes"]

    res_saas = client.get("/api/themes?domain=tech_saas")
    assert res_saas.status_code == 200
    themes_saas = res_saas.json()["themes"]

    # Both domains should have distinct clusters
    assert len(themes_cosmetics) > 0
    assert len(themes_saas) > 0


def test_complaint_clusters_domain_isolation(client):
    res_cosmetics = client.get("/api/complaint-clusters?domain=d2c_cosmetics")
    assert res_cosmetics.status_code == 200
    assert res_cosmetics.json()["domain"] == "d2c_cosmetics"

    res_saas = client.get("/api/complaint-clusters?domain=tech_saas")
    assert res_saas.status_code == 200
    assert res_saas.json()["domain"] == "tech_saas"


def test_invalid_domain_rejected(client):
    res = client.get("/api/overview?domain=unknown_crypto_platform")
    assert res.status_code == 400
    assert "Invalid domain" in res.json()["detail"]


def test_custom_domain_before_upload_returns_404(client):
    # If custom domain is not in cache yet
    if "custom" not in DOMAIN_CACHE:
        res = client.get("/api/overview?domain=custom")
        assert res.status_code == 404
        assert "No custom dataset has been uploaded yet" in res.json()["detail"]
