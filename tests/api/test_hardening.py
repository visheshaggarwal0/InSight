import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import _md_escape, get_domain_bundle, DOMAIN_CACHE, state
from app.core.auth import (
    AuthenticatedUser,
    get_current_user_optional,
    clear_auth_cache,
    _AUTH_CACHE,
    _AUTH_CACHE_LOCK,
)
from app.ml.sentiment import sentiment_model

client = TestClient(app)


def test_md_escape_sanitization():
    """Verify _md_escape neutralizes markdown breakout and HTML markup."""
    # HTML script tags (parentheses are also escaped to prevent markdown link breakouts)
    assert _md_escape("<script>alert('xss')</script>") == "&lt;script&gt;alert\\('xss'\\)&lt;/script&gt;"

    # Markdown links and images
    escaped_link = _md_escape("[Exploit](https://malicious.com)")
    assert "\\[" in escaped_link and "\\]" in escaped_link and "\\(" in escaped_link

    # Markdown headers and formatting
    escaped_header = _md_escape("# P0 CRITICAL **Bold** `code`")
    assert "\\#" in escaped_header
    assert "\\*\\*" in escaped_header
    assert "\\`" in escaped_header

    # Multiline text normalized to single line
    assert _md_escape("Line 1\r\nLine 2\nLine 3") == "Line 1 Line 2 Line 3"

    # Empty string handling
    assert _md_escape("") == ""
    assert _md_escape(None) == ""


def test_auth_token_cache():
    """Verify in-memory token cache prevents repetitive DB round-trips."""
    clear_auth_cache()
    mock_credentials = MagicMock()
    mock_credentials.credentials = "test-session-token-xyz"

    mock_db = MagicMock()
    # Mock row: id, email, name, role, expiresAt
    mock_db.execute.return_value.fetchone.return_value = (
        "usr_123",
        "analyst@example.com",
        "Analyst Alice",
        "analyst",
        None,
    )

    with patch("app.core.auth.SessionLocal", return_value=mock_db):
        # 1. First invocation: cache miss, DB queried
        user1 = get_current_user_optional(mock_credentials)
        assert user1 is not None
        assert user1.id == "usr_123"
        assert user1.email == "analyst@example.com"
        assert mock_db.execute.call_count == 1

        # 2. Second invocation: cache hit, DB NOT queried
        user2 = get_current_user_optional(mock_credentials)
        assert user2 is not None
        assert user2.id == "usr_123"
        assert mock_db.execute.call_count == 1  # Call count remains 1

    clear_auth_cache()


def test_domain_sentiment_model_isolation():
    """Verify that domain bundles maintain their own sentiment models without mutating the global singleton."""
    # Ensure d2c_cosmetics bundle is retrieved
    _, bundle_d2c = get_domain_bundle("d2c_cosmetics")
    d2c_model = bundle_d2c.get("sentiment_model")
    assert d2c_model is not None
    assert d2c_model.is_fitted is True

    # Check global sentiment_model pipeline
    orig_pipeline = sentiment_model.pipeline

    # Ensure tech_saas bundle is retrieved
    _, bundle_saas = get_domain_bundle("tech_saas")
    saas_model = bundle_saas.get("sentiment_model")
    assert saas_model is not None
    assert saas_model.is_fitted is True

    # Models must be separate objects
    assert d2c_model is not saas_model

    # Global sentiment_model singleton must NOT have been overwritten by tech_saas
    assert sentiment_model.pipeline is orig_pipeline


def test_governance_provenance_and_synthetic_disclaimer():
    """Verify /governance exposes honest provenance and disclaimers for real vs synthetic datasets."""
    # Real Sephora domain
    res_d2c = client.get("/api/governance?domain=d2c_cosmetics")
    assert res_d2c.status_code == 200
    data_d2c = res_d2c.json()
    assert data_d2c["evaluation"].get("benchmark_type") == "production_telemetry_weak_labels"
    assert data_d2c["evaluation"].get("synthetic_disclaimer") is None

    # Synthetic SaaS domain
    res_saas = client.get("/api/governance?domain=tech_saas")
    assert res_saas.status_code == 200
    data_saas = res_saas.json()
    assert data_saas["evaluation"].get("benchmark_type") == "synthetic_grammar_benchmark"
    assert "Synthetic benchmark" in data_saas["evaluation"].get("synthetic_disclaimer", "")
    assert "benchmark_note" in data_saas


def test_csv_upload_multi_tenancy_safety():
    """Verify that uploading a CSV does not overwrite state.active_domain for other users."""
    # Ensure default domain is d2c_cosmetics
    res_init = client.get("/api/overview")
    assert res_init.status_code == 200
    initial_domain = res_init.json()["domain"]

    csv_payload = b"review_text,rating\nGreat moisturizer,5\nPump broke immediately,1\nNeutral feedback,3"

    r_upload = client.post(
        "/api/datasets/upload",
        files={"file": ("tenant_isolation_test.csv", csv_payload, "text/csv")}
    )
    assert r_upload.status_code == 200
    upload_data = r_upload.json()
    assert upload_data["status"] == "success"
    assert upload_data["active_domain"] == "custom"
    assert "custom" in DOMAIN_CACHE

    # An independent request without ?domain= must NOT be hijacked to "custom"
    res_independent = client.get("/api/overview")
    assert res_independent.status_code == 200
    assert res_independent.json()["domain"] == initial_domain
