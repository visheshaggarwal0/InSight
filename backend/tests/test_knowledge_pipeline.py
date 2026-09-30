"""test_knowledge_pipeline.py
Comprehensive end-to-end test suite for KnowledgePipeline and POST /api/datasets/upload.

Tests:
  1. Full pipeline ingestion of client CSV with PII, mixed polarity, and custom headers
  2. Exact character offset guarantee on sanitized verbatims
  3. 384D MiniLM embedding generation and presence on all ingested records
  4. End-to-end ingestion of JSON array data
  5. End-to-end ingestion of Excel (.xlsx) file
  6. Quarantine handling on dirty submissions with manifest scoring
  7. API Integration test: TestClient POST /api/datasets/upload -> GET /api/overview
  8. Semantic vector search on newly ingested client data via POST /api/search/semantic
"""

import io
import json
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.data.knowledge_pipeline import knowledge_pipeline, KnowledgePipeline
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_full_pipeline_csv_ingestion():
    csv_content = """customer_feedback,stars,app_release,product_sku
"My email is sarah@example.com and the eye serum is wonderfully cooling, but the pump jammed on day 3 and leaked everywhere.",1,v1.2.0,SKU-EYE-01
"Phone +1-555-0199 for help, love the scent although the cap cracked during delivery.",2,v1.2.0,SKU-EYE-01
"Card 4532-1111-2222-3333 used for purchase. Fast shipping and impeccable quality.",5,v1.2.0,SKU-EYE-01
"Smooth texture, but caused mild redness and stinging on sensitive cheeks.",2,v1.2.0,SKU-EYE-01
"Great hydrating everyday cream for winter.",5,v1.2.0,SKU-EYE-01
"""
    result = knowledge_pipeline.process_and_ingest(
        file_input=csv_content.encode("utf-8"),
        filename="client_feedback.csv",
        domain_id="test_custom",
        persist_db=True
    )

    assert result["status"] == "success"
    assert result["rows_ingested"] == 5
    assert len(result["reviews"]) == 5
    assert len(result["themes"]) > 0

    # 1. PII Scrubbing verified
    first_rev = result["reviews"][0]
    assert "[REDACTED_EMAIL]" in first_rev["redacted_text"]
    assert "sarah@example.com" not in first_rev["redacted_text"]
    assert "EMAIL" in first_rev["pii_detected"]

    # 2. Exact character offset guarantee verified
    span = first_rev["highlight_span"]
    assert span["detected"] is True
    assert first_rev["redacted_text"][span["start"]:span["end"]] == span["text"]
    assert span["text"].startswith("but the pump jammed")

    # 3. 384D embedding verified on every record
    for r in result["reviews"]:
        assert "embedding" in r
        assert len(r["embedding"]) == 384


def test_full_pipeline_json_ingestion():
    json_data = [
        {"comment": "Biometric login crashes the app immediately on startup.", "score": 1, "release": "v2.4.0"},
        {"comment": "Payment failed and funds were stuck in pending limbo.", "score": 2, "release": "v2.4.0"},
        {"comment": "Super clean dashboard, however export CSV times out on large batches.", "score": 3, "release": "v2.4.0"},
        {"comment": "Delightful UX and instant push notifications.", "score": 5, "release": "v2.4.0"},
    ]
    json_bytes = json.dumps(json_data).encode("utf-8")

    result = knowledge_pipeline.process_and_ingest(
        file_input=json_bytes,
        filename="app_reviews.json",
        domain_id="test_json_custom",
        persist_db=True
    )

    assert result["status"] == "success"
    assert result["rows_ingested"] == 4
    assert result["embedding_manifest"]["dimension"] == 384
    assert result["reviews"][0]["overall_severity"] == "P0"  # app crash is P0


def test_full_pipeline_excel_ingestion():
    df = pd.DataFrame({
        "User_Review": [
            "Dropper cracked and shattered in transit.",
            "Face cream feels very greasy and smells off.",
            "Loved the formula and visible glow after 2 weeks."
        ],
        "Rating": [1, 2, 5],
        "Batch": ["Lot-99", "Lot-99", "Lot-99"]
    })
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    result = knowledge_pipeline.process_and_ingest(
        file_input=buffer.getvalue(),
        filename="beauty_export.xlsx",
        domain_id="test_excel_custom",
        persist_db=True
    )

    assert result["status"] == "success"
    assert result["rows_ingested"] == 3
    assert result["reviews"][0]["highlight_span"]["detected"] is True


def test_quarantine_manifest_on_dirty_file():
    dirty_csv = """review_body,stars
"Legitimate defect report stating the screen freezes on checkout.",1
"",1
"ok",5
"Legitimate defect report stating the screen freezes on checkout.",1
"aaaaaaaaaaaaaaaaaaaaaaaa",1
"Another distinct and valid customer review praising quick delivery.",5
"""
    result = knowledge_pipeline.process_and_ingest(
        file_input=dirty_csv.encode("utf-8"),
        filename="dirty_upload.csv",
        domain_id="test_dirty",
        persist_db=False
    )

    assert result["status"] == "success"
    assert result["rows_ingested"] == 2  # 4 rows quarantined/dropped
    q_manifest = result["quality_manifest"]
    assert q_manifest["quarantined_rows"] == 4
    assert q_manifest["duplicate_rows_dropped"] == 1
    assert q_manifest["quality_score_percentage"] < 100.0


def test_api_upload_endpoint_and_semantic_search(client):
    csv_payload = """review,rating,version
"App crashes every time biometric login is attempted.",1,v2.4.0
"Funds were double charged and transaction failed.",1,v2.4.0
"Love the interface but export feature times out.",3,v2.4.0
"Excellent fintech mobile experience overall.",5,v2.4.0
"""
    # 1. Test POST /api/datasets/upload
    files = {"file": ("client_upload.csv", io.BytesIO(csv_payload.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=files)

    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["status"] == "success"
    assert upload_data["active_domain"] == "custom"
    assert upload_data["rows_ingested"] == 4
    assert "schema_report" in upload_data
    assert "quality_manifest" in upload_data
    assert "embedding_manifest" in upload_data

    # 2. Test GET /api/overview reflects custom domain
    overview_res = client.get("/api/overview")
    assert overview_res.status_code == 200
    overview_data = overview_res.json()
    assert overview_data["domain"] == "custom"
    assert overview_data["total_reviews"] == 4

    # 3. Test POST /api/search/semantic vector search on the newly uploaded data
    search_payload = {"query": "biometric fingerprint crash", "domain": "custom", "limit": 2}
    search_res = client.post("/api/search/semantic", json=search_payload)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_matches"] > 0
    # Top match must be the biometric crash review
    top_match = search_data["results"][0]
    assert "crashes" in top_match["redacted_text"].lower()
    assert top_match["similarity_score"] > 0.40

    # 4. Reset active domain to default to avoid polluting other test suites
    client.post("/api/datasets/select", json={"domain": "d2c_cosmetics"})

