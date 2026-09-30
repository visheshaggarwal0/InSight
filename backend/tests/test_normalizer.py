"""test_normalizer.py
Comprehensive test suite for SmartSchemaNormalizer.

Tests:
  1. Standard CSV with explicit column names
  2. Messy CSV with unconventional column headers and extra unmapped metadata
  3. TSV with tab delimiters and star glyph rating parsing ('★★★★')
  4. Semicolon-separated CSV with 'X out of 5' rating strings
  5. JSON Array with 1-10 rating scale normalization
  6. JSON-Lines (.jsonl) parsing
  7. Wrapped JSON Envelope (e.g. {"reviews": [...]}) with 0-100 rating scale
  8. Excel (.xlsx) file parsing
  9. Deterministic ID generation idempotency
  10. Negative test: Error raised when no text column exists
"""

import io
import json
import pytest
import pandas as pd
from app.data.normalizer import SmartSchemaNormalizer, SchemaMappingReport, schema_normalizer


def test_standard_csv_mapping():
    csv_data = """review_text,rating,batch_or_version,sku_or_module,created_at
"The battery life is phenomenal on this phone.",5,v2.4.0,Battery,2026-09-01T12:00:00Z
"Crashes upon biometric login every single time.",1,v2.4.0,Auth,2026-09-02T14:30:00Z
"""
    norm_df, report = schema_normalizer.normalize(csv_data.encode("utf-8"), filename="feedback.csv")
    assert len(norm_df) == 2
    assert report.file_format.startswith("CSV")
    assert report.detected_columns["review_text"] == "review_text"
    assert report.detected_columns["rating"] == "rating"
    assert norm_df.iloc[0]["rating"] == 5
    assert norm_df.iloc[1]["rating"] == 1
    assert norm_df.iloc[0]["sku_or_module"] == "Battery"
    assert norm_df.iloc[0]["id"].startswith("REV-U-")


def test_messy_unconventional_csv_headers():
    csv_data = """user_feedback,stars,app_release,item_name,random_crm_ticket_id,sales_region
"Amazing scent and packaging was pristine.",4.0,Batch-99,Ceramide Cream,CRM-8812,North America
"Pump dispenser broke on day 3 and leaked.",1.0,Batch-99,Ceramide Cream,CRM-8813,Europe
"""
    norm_df, report = schema_normalizer.normalize(csv_data.encode("utf-8"), filename="client_export.csv")
    assert len(norm_df) == 2
    assert report.detected_columns["review_text"] == "user_feedback"
    assert report.detected_columns["rating"] == "stars"
    assert report.detected_columns["batch_or_version"] == "app_release"
    assert report.detected_columns["product_name"] == "item_name"
    assert "random_crm_ticket_id" in report.unmapped_columns
    assert "sales_region" in report.unmapped_columns
    assert norm_df.iloc[0]["extra_metadata"]["random_crm_ticket_id"] == "CRM-8812"
    assert norm_df.iloc[1]["extra_metadata"]["sales_region"] == "Europe"


def test_tsv_and_star_glyph_ratings():
    tsv_data = "verbatim\tstar_rating\tbuild\nGreat tool!\t★★★★\tv1.2.0\nDisaster\t★\tv1.2.0\n"
    norm_df, report = schema_normalizer.normalize(tsv_data.encode("utf-8"), filename="reviews.tsv")
    assert len(norm_df) == 2
    assert report.file_format == "TSV"
    assert norm_df.iloc[0]["rating"] == 4
    assert norm_df.iloc[1]["rating"] == 1


def test_semicolon_delimited_and_fractional_ratings():
    data = 'comment;score;date\n"App freezes on payment";"1 out of 5";2026-08-15\n"Super smooth";"5/5";2026-08-16\n'
    norm_df, report = schema_normalizer.normalize(data.encode("utf-8"), filename="export_eu.csv")
    assert len(norm_df) == 2
    assert norm_df.iloc[0]["rating"] == 1
    assert norm_df.iloc[1]["rating"] == 5


def test_json_array_with_ten_point_scale():
    json_data = json.dumps([
        {"message": "Flawless UI experience", "grade": 10, "tag": "UI"},
        {"message": "Average performance", "grade": 5, "tag": "Performance"},
        {"message": "Terrible checkout bug", "grade": 2, "tag": "Checkout"},
    ])
    norm_df, report = schema_normalizer.normalize(json_data.encode("utf-8"), filename="survey.json")
    assert len(norm_df) == 3
    assert report.file_format == "JSON Array"
    assert "1-10" in report.rating_scale_detected
    assert norm_df.iloc[0]["rating"] == 5
    assert norm_df.iloc[1]["rating"] == 3
    assert norm_df.iloc[2]["rating"] == 1


def test_json_lines_format():
    jsonl_lines = (
        '{"critique": "Face serum burns on application", "stars": 1, "cohort": "Lot-24C"}\n'
        '{"critique": "Hydrates nicely throughout winter", "stars": 5, "cohort": "Lot-24A"}\n'
    )
    norm_df, report = schema_normalizer.normalize(jsonl_lines.encode("utf-8"), filename="logs.jsonl")
    assert len(norm_df) == 2
    assert "JSON-Lines" in report.file_format
    assert norm_df.iloc[0]["batch_or_version"] == "Lot-24C"
    assert norm_df.iloc[0]["rating"] == 1


def test_wrapped_json_envelope_with_hundred_scale():
    envelope = {
        "status": "success",
        "records": [
            {"description": "Best CRM software ever used", "satisfaction": 95},
            {"description": "Export feature completely failed", "satisfaction": 15},
        ]
    }
    json_bytes = json.dumps(envelope).encode("utf-8")
    norm_df, report = schema_normalizer.normalize(json_bytes, filename="crm_export.json")
    assert len(norm_df) == 2
    assert "JSON Envelope" in report.file_format
    assert "0-100" in report.rating_scale_detected
    assert norm_df.iloc[0]["rating"] == 5
    assert norm_df.iloc[1]["rating"] == 2


def test_excel_file_ingestion():
    raw_df = pd.DataFrame({
        "Customer_Review": ["Great packaging", "Damaged bottle on arrival"],
        "User_Rating": [5, 1],
        "Product_Model": ["Hydro Cream", "Hydro Cream"],
        "Dispatch_Batch": ["B-101", "B-101"]
    })
    buffer = io.BytesIO()
    raw_df.to_excel(buffer, index=False)
    buffer.seek(0)

    norm_df, report = schema_normalizer.normalize(buffer.getvalue(), filename="client_feedback.xlsx")
    assert len(norm_df) == 2
    assert "Excel" in report.file_format
    assert norm_df.iloc[0]["rating"] == 5
    assert norm_df.iloc[1]["rating"] == 1
    assert norm_df.iloc[0]["product_name"] == "Hydro Cream"
    assert norm_df.iloc[0]["batch_or_version"] == "B-101"


def test_deterministic_id_idempotence():
    text = "The biometric login works 50% of the time."
    csv_content = f'review,rating\n"{text}",2\n'
    norm_df1, _ = schema_normalizer.normalize(csv_content.encode("utf-8"), filename="test1.csv")
    norm_df2, _ = schema_normalizer.normalize(csv_content.encode("utf-8"), filename="test2.csv")

    assert norm_df1.iloc[0]["id"] == norm_df2.iloc[0]["id"]
    assert norm_df1.iloc[0]["id"].startswith("REV-U-")


def test_missing_text_column_raises_error():
    bad_csv = "user_id,rating,date\n101,5,2026-09-01\n102,4,2026-09-02\n"
    with pytest.raises(ValueError, match="Could not identify a review text column"):
        schema_normalizer.normalize(bad_csv.encode("utf-8"), filename="bad.csv")
