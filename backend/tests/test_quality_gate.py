"""test_quality_gate.py
Comprehensive test suite for DataQualityGate.

Tests:
  1. Empty and sentinel placeholder text quarantine (EMPTY_TEXT)
  2. Degenerate short text and filler quarantine (DEGENERATE_SHORT_TEXT)
  3. Character spam repetition quarantine (REPETITIVE_CHARACTER_SPAM)
  4. Duplicate verbatim detection and deduplication (DUPLICATE_TEXT)
  5. Rating clamping to [1, 5] with warnings
  6. Future / Epoch date boundary normalization
  7. Long text overflow truncation
  8. Empty dataframe handling
  9. End-to-end chaining: SmartSchemaNormalizer -> DataQualityGate
"""

import pytest
import pandas as pd
from app.data.normalizer import schema_normalizer
from app.data.quality_gate import DataQualityGate, data_quality_gate, QualityGateManifest


def test_empty_and_sentinel_text_quarantine():
    df = pd.DataFrame([
        {"id": "REV-1", "raw_text": "   ", "rating": 3, "created_at": "2026-09-01T00:00:00Z"},
        {"id": "REV-2", "raw_text": "nan", "rating": 3, "created_at": "2026-09-01T00:00:00Z"},
        {"id": "REV-3", "raw_text": "Valid customer review stating the pump broke on day 3.", "rating": 1, "created_at": "2026-09-01T00:00:00Z"},
    ])
    clean_df, manifest = data_quality_gate.validate_and_quarantine(df)
    assert len(clean_df) == 1
    assert manifest.total_input_rows == 3
    assert manifest.quarantined_rows == 2
    assert manifest.rejection_breakdown["EMPTY_TEXT"] == 2
    assert clean_df.iloc[0]["id"] == "REV-3"


def test_degenerate_short_text_quarantine():
    df = pd.DataFrame([
        {"id": "REV-1", "raw_text": "ok", "rating": 5, "created_at": "2026-09-01T00:00:00Z"},
        {"id": "REV-2", "raw_text": "good", "rating": 5, "created_at": "2026-09-01T00:00:00Z"},
        {"id": "REV-3", "raw_text": "asdf", "rating": 2, "created_at": "2026-09-01T00:00:00Z"},
        {"id": "REV-4", "raw_text": "The app crashes on biometric auth every single morning.", "rating": 1, "created_at": "2026-09-01T00:00:00Z"},
    ])
    clean_df, manifest = data_quality_gate.validate_and_quarantine(df)
    assert len(clean_df) == 1
    assert manifest.rejection_breakdown["DEGENERATE_SHORT_TEXT"] == 3
    assert clean_df.iloc[0]["id"] == "REV-4"


def test_repetitive_character_spam():
    df = pd.DataFrame([
        {"id": "REV-1", "raw_text": "aaaaaaaaaaaaaaaaaaaaa", "rating": 1, "created_at": "2026-09-01T00:00:00Z"},
        {"id": "REV-2", "raw_text": ".....................", "rating": 1, "created_at": "2026-09-01T00:00:00Z"},
        {"id": "REV-3", "raw_text": "Formula reformulations caused skin tingling and rash.", "rating": 1, "created_at": "2026-09-01T00:00:00Z"},
    ])
    clean_df, manifest = data_quality_gate.validate_and_quarantine(df)
    assert len(clean_df) == 1
    assert manifest.rejection_breakdown["REPETITIVE_CHARACTER_SPAM"] == 2
    assert clean_df.iloc[0]["id"] == "REV-3"


def test_duplicate_text_deduplication():
    df = pd.DataFrame([
        {"id": "REV-1", "raw_text": "Great hydrating face cream for sensitive skin.", "rating": 5, "created_at": "2026-09-01T00:00:00Z"},
        {"id": "REV-2", "raw_text": "great hydrating face cream for sensitive skin. ", "rating": 5, "created_at": "2026-09-01T01:00:00Z"},
        {"id": "REV-3", "raw_text": "Completely different comment about fast shipping.", "rating": 4, "created_at": "2026-09-01T02:00:00Z"},
    ])
    clean_df, manifest = data_quality_gate.validate_and_quarantine(df)
    assert len(clean_df) == 2
    assert manifest.duplicate_rows_dropped == 1
    assert manifest.rejection_breakdown["DUPLICATE_TEXT"] == 1
    assert clean_df.iloc[0]["id"] == "REV-1"
    assert clean_df.iloc[1]["id"] == "REV-3"


def test_rating_clamping():
    df = pd.DataFrame([
        {"id": "REV-1", "raw_text": "Severe allergic reaction and swollen eyes.", "rating": -5, "created_at": "2026-09-01T00:00:00Z"},
        {"id": "REV-2", "raw_text": "Best skincare serum on the market right now.", "rating": 12, "created_at": "2026-09-01T00:00:00Z"},
    ])
    clean_df, manifest = data_quality_gate.validate_and_quarantine(df)
    assert len(clean_df) == 2
    assert clean_df.iloc[0]["rating"] == 1  # clamped from -5 to 1
    assert clean_df.iloc[1]["rating"] == 5  # clamped from 12 to 5
    assert manifest.total_warnings == 2


def test_future_and_epoch_date_sanitization():
    df = pd.DataFrame([
        {"id": "REV-1", "raw_text": "Bug report about export timeout error.", "rating": 2, "created_at": "1970-01-01T00:00:00Z"},
        {"id": "REV-2", "raw_text": "Another bug report about billing failure.", "rating": 1, "created_at": "2099-12-31T00:00:00Z"},
    ])
    clean_df, manifest = data_quality_gate.validate_and_quarantine(df)
    assert len(clean_df) == 2
    assert manifest.total_warnings == 2
    # Verify dates were normalized away from 1970 and 2099
    assert not clean_df.iloc[0]["created_at"].startswith("1970")
    assert not clean_df.iloc[1]["created_at"].startswith("2099")


def test_text_length_truncation():
    long_text = "Defect complaint detailing unexpected biometric failure and memory leaks in production. " * 30
    df = pd.DataFrame([
        {"id": "REV-1", "raw_text": long_text, "rating": 2, "created_at": "2026-09-01T00:00:00Z"}
    ])
    gate = DataQualityGate(max_text_len=100)
    clean_df, manifest = gate.validate_and_quarantine(df)
    assert len(clean_df) == 1
    assert len(clean_df.iloc[0]["raw_text"]) == 100
    assert manifest.total_warnings == 1


def test_empty_dataframe():
    df = pd.DataFrame(columns=["id", "raw_text", "rating", "created_at"])
    clean_df, manifest = data_quality_gate.validate_and_quarantine(df)
    assert len(clean_df) == 0
    assert manifest.quality_score_percentage == 100.0


def test_end_to_end_normalizer_and_quality_gate_chain():
    raw_csv = """feedback_notes,stars,cohort
"Authentic review with clear feedback on slow load times.",2,v2.4.0
"",1,v2.4.0
"ok",5,v2.4.0
"Authentic review with clear feedback on slow load times.",2,v2.4.0
"Smooth and responsive experience so far.",5,v2.4.0
"""
    norm_df, schema_report = schema_normalizer.normalize(raw_csv.encode("utf-8"), filename="dirty.csv")
    assert len(norm_df) == 5

    clean_df, quality_manifest = data_quality_gate.validate_and_quarantine(norm_df)
    assert len(clean_df) == 2  # 1 empty, 1 degenerate 'ok', 1 duplicate dropped
    assert quality_manifest.quarantined_rows == 3
    assert quality_manifest.duplicate_rows_dropped == 1
    assert quality_manifest.quality_score_percentage < 100.0
    assert len(quality_manifest.quarantined_sample) == 3
