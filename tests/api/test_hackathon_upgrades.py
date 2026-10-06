import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_copilot_ask_endpoint():
    """Verify AI Copilot generates evidence-grounded answers with citations."""
    payload = {"query": "What are our worst P0 defects and how many customers are affected?"}
    response = client.post("/api/copilot/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "headline" in data
    assert "answer" in data
    assert "verdict" in data
    assert "citations" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0
    assert len(data["citations"]) > 0

def test_copilot_briefing_endpoint():
    """Verify executive one-pager briefing generation."""
    response = client.get("/api/copilot/briefing")
    assert response.status_code == 200
    data = response.json()
    assert "report_title" in data
    assert "executive_summary" in data
    assert "kpis" in data
    assert "threat_radar" in data
    assert "sprint_backlog_recommendations" in data
    assert data["kpis"]["total_reviews"] > 0

def test_benchmark_cohorts_and_compare():
    """Verify head-to-head cohort delta analysis."""
    cohorts_res = client.get("/api/benchmark/cohorts")
    assert cohorts_res.status_code == 200
    cohorts_data = cohorts_res.json()
    assert "batches" in cohorts_data
    assert len(cohorts_data["batches"]) >= 2

    b = cohorts_data["batches"]
    comp_res = client.post("/api/benchmark/compare", json={
        "compare_type": "batch",
        "cohort_a": b[-2],
        "cohort_b": b[-1]
    })
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert "cohort_a" in comp_data
    assert "cohort_b" in comp_data
    assert "comparison" in comp_data
    assert "verdict" in comp_data["comparison"]
    assert "rating_delta" in comp_data["comparison"]
    assert "theme_shifts" in comp_data["comparison"]

def test_action_matrix_endpoint():
    """Verify CSAT ROI impact vs effort prioritization matrix."""
    response = client.get("/api/action/matrix")
    assert response.status_code == 200
    data = response.json()
    assert "baseline_csat" in data
    assert "projected_target_csat" in data
    assert "items" in data
    assert "quadrant_counts" in data
    assert len(data["items"]) > 0
    # Check that item contains story points and projected CSAT lift
    first = data["items"][0]
    assert "story_points" in first
    assert "projected_csat_lift" in first
    assert "impact_score" in first

def test_anomaly_injection_and_reset():
    """Verify interactive defect surge simulation and baseline restoration."""
    # 1. Inject anomaly
    inject_res = client.post("/api/drift/simulate-anomaly", json={"scenario": "chemical_burn"})
    assert inject_res.status_code == 200
    inject_data = inject_res.json()
    assert inject_data["status"] == "anomaly_injected"
    assert inject_data["alert"]["psi_score"] > 0.25 # Violates threshold
    assert "emergency_incident_ticket" in inject_data

    # 2. Check drift endpoint now includes the simulated alert
    drift_res = client.get("/api/drift")
    assert drift_res.status_code == 200
    alerts = drift_res.json().get("alerts", [])
    assert any(a.get("is_simulated") for a in alerts)

    # 3. Reset anomaly
    reset_res = client.post("/api/drift/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "reset_successful"

    # 4. Check clean baseline
    drift_clean = client.get("/api/drift")
    assert drift_clean.status_code == 200
    clean_alerts = drift_clean.json().get("alerts", [])
    assert not any(a.get("is_simulated") for a in clean_alerts)
