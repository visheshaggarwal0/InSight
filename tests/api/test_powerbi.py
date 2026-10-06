import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_powerbi_config_get_and_post(client):
    # Test GET config
    res = client.get("/api/powerbi/config")
    assert res.status_code == 200
    cfg = res.json()
    assert "embed_url" in cfg
    assert "report_title" in cfg
    assert "demo_url" in cfg

    # Test POST config
    sample_url = "https://app.powerbi.com/view?r=test_token"
    post_res = client.post("/api/powerbi/config", json={
        "embed_url": sample_url,
        "report_title": "Test Executive Report"
    })
    assert post_res.status_code == 200
    updated = post_res.json()
    assert updated["embed_url"] == sample_url
    assert updated["report_title"] == "Test Executive Report"
    assert updated["is_configured"] is True

    # Reset back to empty
    client.post("/api/powerbi/config", json={
        "embed_url": "",
        "report_title": "InSight Executive Review Intelligence"
    })

def test_powerbi_data_summary(client):
    res = client.get("/api/powerbi/data/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_reviews" in data
    assert "net_sentiment_score" in data
    assert "defect_surge_rate_pct" in data
    assert "actionable_rate_pct" in data
    assert "pii_compliance_rate_pct" in data
    assert data["total_reviews"] > 0

def test_powerbi_data_reviews_json_and_csv(client):
    # JSON reviews feed
    res = client.get("/api/powerbi/data/reviews?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "total_rows" in data
    assert len(data["data"]) == 10
    first = data["data"][0]
    assert "Review_ID" in first
    assert "Rating" in first
    assert "Calibrated_Sentiment" in first
    assert "Is_Actionable" in first

    # CSV reviews stream
    csv_res = client.get("/api/powerbi/data/reviews.csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "Review_ID,Domain,Product_Name" in csv_res.text

def test_powerbi_themes_and_drift(client):
    themes_res = client.get("/api/powerbi/data/themes")
    assert themes_res.status_code == 200
    assert "data" in themes_res.json()

    drift_res = client.get("/api/powerbi/data/drift")
    assert drift_res.status_code == 200
    assert "data" in drift_res.json()

def test_powerbi_pbids_and_guide(client):
    # PBIDS connection file
    pbids_res = client.get("/api/powerbi/connector/pbids")
    assert pbids_res.status_code == 200
    pbids = pbids_res.json()
    assert pbids["version"] == "0.1"
    assert len(pbids["connections"]) > 0
    assert pbids["connections"][0]["connectionType"] == "Web"

    # Guide with DAX and M-Query
    guide_res = client.get("/api/powerbi/guide")
    assert guide_res.status_code == 200
    guide = guide_res.json()
    assert "power_query_m" in guide
    assert "dax_measures" in guide
    assert len(guide["dax_measures"]) >= 6
    assert "api_urls" in guide
