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
    assert "accuracy" in data["evaluation"]
    assert "macro_f1" in data["evaluation"]
