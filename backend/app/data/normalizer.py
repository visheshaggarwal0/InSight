"""normalizer.py
Enterprise Ingestion & Smart Schema Normalizer for InSight.

Provides dynamic, format-agnostic ingestion supporting:
  - CSV (comma, tab, semicolon, pipe delimiters)
  - TSV
  - JSON (Arrays of objects, JSON-Lines / NDJSON, or wrapped {"data": [...]})
  - Excel (.xlsx, .xls)

Features:
  - Intelligent fuzzy column mapping with anti-collision guards
  - Dynamic rating scale detection and normalization to [1, 5] integer scale
  - Robust multi-encoding decoding (UTF-8, UTF-8-BOM, Latin-1, Windows-1252)
  - Deterministic SHA-256 record ID generation
  - Zero data loss: unmapped columns preserved in `extra_metadata`
  - Structured `SchemaMappingReport` for auditability and client feedback
"""

from __future__ import annotations

import io
import re
import csv
import json
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional, Union

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Target Standard Schema Fields & Prioritized Fuzzy Aliases
# ---------------------------------------------------------------------------

# Positive aliases for text column matching
_TEXT_CANDIDATES = [
    "review_text", "review", "text", "comment", "feedback",
    "customer_review", "body", "content", "message", "verbatim",
    "complaint", "notes", "description", "opinion", "user_review",
    "user_feedback", "review_body", "full_review", "critique"
]

# Negative patterns that must NOT be mapped as review text
_TEXT_EXCLUSION_PATTERNS = [
    r"_?id$", r"^id$", r"url$", r"link$", r"count$", r"score$",
    r"length$", r"date$", r"time$", r"rating$", r"author$", r"name$"
]

_RATING_CANDIDATES = [
    "rating", "score", "stars", "star_rating", "grade", "val",
    "rate", "user_rating", "review_rating", "star", "satisfaction"
]

_VERSION_CANDIDATES = [
    "version", "batch", "release", "app_version", "build", "lot",
    "manufacturing_lot", "cohort", "quarter", "revision", "app_release",
    "batch_number", "lot_number", "software_version", "model_version"
]

_SKU_MODULE_CANDIDATES = [
    "sku", "module", "feature", "category", "component", "subsystem",
    "feature_area", "service", "item_code", "sku_id", "product_id",
    "tag", "topic", "department"
]

_PRODUCT_CANDIDATES = [
    "product_name", "product", "item", "item_name", "app_name",
    "brand", "brand_name", "title", "application", "device"
]

_CHANNEL_CANDIDATES = [
    "channel", "source", "platform", "store", "app_store", "origin",
    "marketplace", "device_type", "os", "client"
]

_DATE_CANDIDATES = [
    "timestamp", "created_at", "date", "submission_time", "time",
    "review_date", "created_date", "datetime", "published_at",
    "post_date", "submitted_at"
]


@dataclass
class SchemaMappingReport:
    """Detailed audit report of how raw client columns mapped to standard schema."""
    file_format: str
    total_raw_rows: int
    detected_columns: Dict[str, str] = field(default_factory=dict)
    unmapped_columns: List[str] = field(default_factory=list)
    column_confidence: Dict[str, float] = field(default_factory=dict)
    rating_scale_detected: str = "1-5"
    date_parsing_success_rate: float = 1.0
    preview_sample: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SmartSchemaNormalizer:
    """
    Enterprise-grade dynamic schema normalizer.
    Converts heterogeneous client data files into the standardized InSight internal schema.
    """

    def __init__(self, default_domain: str = "custom"):
        self.default_domain = default_domain

    @staticmethod
    def _clean_column_name(col: str) -> str:
        """Normalizes column names for fuzzy comparison."""
        cleaned = str(col).strip().lower()
        cleaned = re.sub(r"[\s\-_.]+", "_", cleaned)
        cleaned = re.sub(r"[^\w]", "", cleaned)
        return cleaned

    def _fuzzy_match_column(
        self,
        columns: List[str],
        candidates: List[str],
        exclusions: Optional[List[str]] = None,
        used_cols: Optional[set] = None
    ) -> Tuple[Optional[str], float]:
        """
        Matches standard field against available raw columns using priority scoring.
        Returns (matched_source_col, confidence_score).
        """
        used = used_cols or set()
        cleaned_map = {col: self._clean_column_name(col) for col in columns if col not in used}

        # Check exclusions first
        if exclusions:
            for raw_col, clean_col in list(cleaned_map.items()):
                for exc in exclusions:
                    if re.search(exc, clean_col):
                        cleaned_map.pop(raw_col, None)
                        break

        # Priority 1: Exact matches
        for cand in candidates:
            for raw_col, clean_col in cleaned_map.items():
                if clean_col == cand:
                    return raw_col, 1.0

        # Priority 2: Substring prefix/suffix match
        for cand in candidates:
            for raw_col, clean_col in cleaned_map.items():
                if clean_col.startswith(cand) or clean_col.endswith(cand):
                    return raw_col, 0.85

        # Priority 3: General substring inclusion
        for cand in candidates:
            for raw_col, clean_col in cleaned_map.items():
                if cand in clean_col:
                    return raw_col, 0.70

        return None, 0.0

    @staticmethod
    def _parse_star_rating_string(val: Any) -> Optional[float]:
        """Parses star glyphs, 'X out of Y', or fractional ratings from strings."""
        if pd.isna(val) or val is None:
            return None
        if isinstance(val, (int, float, np.integer, np.floating)):
            return float(val)

        s = str(val).strip()
        # Check star glyphs: ★ or ⭐
        star_count = s.count("★") + s.count("⭐")
        if star_count > 0:
            return float(star_count)

        # Pattern: "4 out of 5" or "4 / 5" or "4/5"
        slash_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:/|out\s+of)\s*(\d+(?:\.\d+)?)", s, re.IGNORECASE)
        if slash_match:
            num = float(slash_match.group(1))
            denom = float(slash_match.group(2))
            if denom > 0:
                return (num / denom) * 5.0

        # Single numeric token inside string (e.g. "4 stars", "rating: 3")
        num_match = re.search(r"\b(\d+(?:\.\d+)?)\b", s)
        if num_match:
            return float(num_match.group(1))

        return None

    def normalize_ratings(self, series: pd.Series) -> Tuple[pd.Series, str]:
        """
        Normalizes any rating scale (1-5, 1-10, 0-100, stars) to standard integer [1, 5].
        Returns (normalized_series, detected_scale_description).
        """
        # Parse all entries to floats
        parsed_floats = series.apply(self._parse_star_rating_string)
        valid_numeric = parsed_floats.dropna()

        if len(valid_numeric) == 0:
            return pd.Series(3, index=series.index), "Default (3 Stars, unparseable)"

        max_val = valid_numeric.quantile(0.99)
        min_val = valid_numeric.min()

        scale_desc = "1-5"
        if max_val > 10.0:
            # 0-100 scale (e.g. percentage or NPS)
            scale_desc = "0-100 (rescaled to 1-5)"
            normalized = parsed_floats.apply(
                lambda v: 3 if pd.isna(v) else int(round(np.clip(1 + (v / 100.0) * 4, 1, 5)))
            )
        elif max_val > 5.0:
            # 1-10 scale
            scale_desc = "1-10 (rescaled to 1-5)"
            normalized = parsed_floats.apply(
                lambda v: 3 if pd.isna(v) else int(round(np.clip(1 + ((v - 1.0) / 9.0) * 4, 1, 5)))
            )
        else:
            # 1-5 scale standard
            scale_desc = "1-5 Standard"
            normalized = parsed_floats.apply(
                lambda v: 3 if pd.isna(v) else int(round(np.clip(v, 1, 5)))
            )

        return normalized.astype(int), scale_desc

    @staticmethod
    def _parse_timestamp(val: Any) -> Tuple[str, bool]:
        """Parses heterogeneous dates to ISO-8601 UTC string."""
        if pd.isna(val) or val is None or str(val).strip() == "":
            return datetime.now(timezone.utc).isoformat(), False

        # If already datetime
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.isoformat(), True

        # Try pandas to_datetime
        try:
            dt = pd.to_datetime(val)
            if pd.isna(dt):
                return datetime.now(timezone.utc).isoformat(), False
            return dt.isoformat(), True
        except Exception:
            return datetime.now(timezone.utc).isoformat(), False

    def load_raw_data(
        self,
        file_input: Union[bytes, str, io.BytesIO, io.StringIO],
        filename: Optional[str] = None
    ) -> Tuple[pd.DataFrame, str]:
        """
        Reads input into a raw DataFrame supporting CSV, TSV, JSON, and Excel.
        Returns (DataFrame, detected_format).
        """
        # Determine format hint from filename if present
        fn_lower = (filename or "").lower()
        
        # Convert bytes to stream if needed
        if isinstance(file_input, bytes):
            stream = io.BytesIO(file_input)
        elif isinstance(file_input, str):
            if file_input.strip().startswith(("{", "[")):
                # JSON string literal
                stream = io.StringIO(file_input)
                fn_lower = "data.json"
            else:
                # File path
                return self._load_from_filepath(file_input)
        else:
            stream = file_input

        # 1. Try Excel if filename suggests it
        if fn_lower.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(stream)
                return df, "Excel (.xlsx)"
            except Exception as e:
                logger.warning(f"Excel parse failed: {e}. Falling back to CSV sniffing.")
                if hasattr(stream, "seek"):
                    stream.seek(0)

        # 2. Try JSON
        if fn_lower.endswith((".json", ".jsonl", ".ndjson")):
            try:
                if hasattr(stream, "seek"):
                    stream.seek(0)
                content = stream.read()
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="ignore")
                
                # Check if JSON lines
                if fn_lower.endswith((".jsonl", ".ndjson")) or (content.strip().startswith("{") and "\n" in content.strip()):
                    try:
                        df = pd.read_json(io.StringIO(content), lines=True)
                        return df, "JSON-Lines (.jsonl)"
                    except Exception:
                        pass

                # Parse JSON standard
                parsed_json = json.loads(content)
                if isinstance(parsed_json, list):
                    return pd.DataFrame(parsed_json), "JSON Array"
                elif isinstance(parsed_json, dict):
                    # Check for envelope keys
                    for key in ["reviews", "data", "items", "records", "feedback", "results"]:
                        if key in parsed_json and isinstance(parsed_json[key], list):
                            return pd.DataFrame(parsed_json[key]), f"JSON Envelope ('{key}')"
                    # Single dict with list values
                    return pd.DataFrame([parsed_json]), "JSON Single Object"
            except Exception as e:
                logger.warning(f"JSON parse failed: {e}. Falling back to CSV.")
                if hasattr(stream, "seek"):
                    stream.seek(0)

        # 3. CSV / TSV with robust multi-encoding & delimiter sniffing
        if hasattr(stream, "seek"):
            stream.seek(0)
        raw_bytes = stream.read() if hasattr(stream, "read") else b""
        if isinstance(raw_bytes, str):
            raw_bytes = raw_bytes.encode("utf-8")

        for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                text_content = raw_bytes.decode(encoding)
                # Delimiter sniff
                sample = text_content[:4096]
                delimiter = ","
                if "\t" in sample and sample.count("\t") > sample.count(","):
                    delimiter = "\t"
                elif ";" in sample and sample.count(";") > sample.count(","):
                    delimiter = ";"
                elif "|" in sample and sample.count("|") > sample.count(","):
                    delimiter = "|"

                df = pd.read_csv(io.StringIO(text_content), sep=delimiter)
                format_name = "TSV" if delimiter == "\t" else f"CSV (sep='{delimiter}', enc={encoding})"
                return df, format_name
            except Exception:
                continue

        # Ultimate fallback
        text_content = raw_bytes.decode("utf-8", errors="replace")
        df = pd.read_csv(io.StringIO(text_content), sep=None, engine="python")
        return df, "CSV (Auto-sniffed fallback)"

    def _load_from_filepath(self, filepath: str) -> Tuple[pd.DataFrame, str]:
        """Loads data directly from a local filesystem path."""
        with open(filepath, "rb") as f:
            return self.load_raw_data(f.read(), filename=filepath)

    def normalize(
        self,
        file_input: Union[bytes, str, io.BytesIO, io.StringIO, pd.DataFrame],
        filename: Optional[str] = None
    ) -> Tuple[pd.DataFrame, SchemaMappingReport]:
        """
        End-to-end normalization entrypoint.
        Ingests client input, identifies columns, standardizes schema,
        generates deterministic record IDs, and outputs audit report.
        """
        # 1. Ingest into DataFrame
        if isinstance(file_input, pd.DataFrame):
            raw_df = file_input.copy()
            detected_format = "DataFrame Direct"
        else:
            raw_df, detected_format = self.load_raw_data(file_input, filename=filename)

        raw_columns = list(raw_df.columns)
        total_rows = len(raw_df)
        used_columns = set()
        detected_mapping: Dict[str, str] = {}
        confidences: Dict[str, float] = {}

        # 2. Map Review Text (MANDATORY)
        text_col, text_conf = self._fuzzy_match_column(
            raw_columns, _TEXT_CANDIDATES, exclusions=_TEXT_EXCLUSION_PATTERNS, used_cols=used_columns
        )
        if not text_col:
            raise ValueError(
                f"Could not identify a review text column. Found columns: {raw_columns}. "
                f"Please ensure your data contains a text column like 'review', 'comment', or 'feedback'."
            )
        detected_mapping["review_text"] = text_col
        confidences["review_text"] = text_conf
        used_columns.add(text_col)

        # 3. Map Rating (OPTIONAL)
        rating_col, rating_conf = self._fuzzy_match_column(
            raw_columns, _RATING_CANDIDATES, used_cols=used_columns
        )
        if rating_col:
            detected_mapping["rating"] = rating_col
            confidences["rating"] = rating_conf
            used_columns.add(rating_col)

        # 4. Map Batch / Version (OPTIONAL)
        version_col, version_conf = self._fuzzy_match_column(
            raw_columns, _VERSION_CANDIDATES, used_cols=used_columns
        )
        if version_col:
            detected_mapping["batch_or_version"] = version_col
            confidences["batch_or_version"] = version_conf
            used_columns.add(version_col)

        # 5. Map SKU / Module (OPTIONAL)
        sku_col, sku_conf = self._fuzzy_match_column(
            raw_columns, _SKU_MODULE_CANDIDATES, used_cols=used_columns
        )
        if sku_col:
            detected_mapping["sku_or_module"] = sku_col
            confidences["sku_or_module"] = sku_conf
            used_columns.add(sku_col)

        # 6. Map Product Name (OPTIONAL)
        prod_col, prod_conf = self._fuzzy_match_column(
            raw_columns, _PRODUCT_CANDIDATES, used_cols=used_columns
        )
        if prod_col:
            detected_mapping["product_name"] = prod_col
            confidences["product_name"] = prod_conf
            used_columns.add(prod_col)

        # 7. Map Channel / Source (OPTIONAL)
        channel_col, channel_conf = self._fuzzy_match_column(
            raw_columns, _CHANNEL_CANDIDATES, used_cols=used_columns
        )
        if channel_col:
            detected_mapping["channel"] = channel_col
            confidences["channel"] = channel_conf
            used_columns.add(channel_col)

        # 8. Map Timestamp (OPTIONAL)
        date_col, date_conf = self._fuzzy_match_column(
            raw_columns, _DATE_CANDIDATES, used_cols=used_columns
        )
        if date_col:
            detected_mapping["created_at"] = date_col
            confidences["created_at"] = date_conf
            used_columns.add(date_col)

        # Unmapped extra columns
        unmapped_cols = [c for c in raw_columns if c not in used_columns]

        # -------------------------------------------------------------------
        # Build Normalized DataFrame
        # -------------------------------------------------------------------
        norm_df = pd.DataFrame(index=raw_df.index)

        # Text column (clean string)
        norm_df["raw_text"] = raw_df[text_col].fillna("").astype(str).str.strip()

        # Rating column with scale normalization
        if rating_col:
            norm_ratings, scale_desc = self.normalize_ratings(raw_df[rating_col])
            norm_df["rating"] = norm_ratings
        else:
            norm_df["rating"] = 3
            scale_desc = "Default (3 Stars, no column provided)"

        # Product name
        if prod_col:
            norm_df["product_name"] = raw_df[prod_col].fillna("Custom Product").astype(str)
        else:
            norm_df["product_name"] = "Custom Product"

        # SKU or Module
        if sku_col:
            norm_df["sku_or_module"] = raw_df[sku_col].fillna("General").astype(str)
        else:
            norm_df["sku_or_module"] = "General"

        # Batch or Version
        if version_col:
            norm_df["batch_or_version"] = raw_df[version_col].fillna("Batch-Custom").astype(str)
        else:
            norm_df["batch_or_version"] = "Batch-Custom"

        # Channel
        if channel_col:
            norm_df["channel"] = raw_df[channel_col].fillna("Client Upload").astype(str)
        else:
            norm_df["channel"] = "Client Upload"

        # Timestamp
        date_successes = 0
        parsed_dates = []
        if date_col:
            for val in raw_df[date_col]:
                iso_str, success = self._parse_timestamp(val)
                parsed_dates.append(iso_str)
                if success:
                    date_successes += 1
            date_rate = date_successes / max(1, total_rows)
        else:
            now_iso = datetime.now(timezone.utc).isoformat()
            parsed_dates = [now_iso] * total_rows
            date_rate = 1.0

        norm_df["created_at"] = parsed_dates
        norm_df["domain"] = self.default_domain

        # Preserve unmapped columns in extra_metadata
        if unmapped_cols:
            extra_dicts = []
            for _, row in raw_df[unmapped_cols].iterrows():
                row_dict = {
                    k: (None if pd.isna(v) else v)
                    for k, v in row.to_dict().items()
                }
                extra_dicts.append(row_dict)
            norm_df["extra_metadata"] = extra_dicts
        else:
            norm_df["extra_metadata"] = [{} for _ in range(total_rows)]

        # Generate deterministic IDs: REV-U-{SHA256[:12]}
        ids = []
        for idx, row in norm_df.iterrows():
            ts_key = row["created_at"] if date_col else "static_ts"
            token = f"{row['raw_text']}_{ts_key}_{idx}".encode("utf-8")
            hash_sig = hashlib.sha256(token).hexdigest()[:12].upper()
            ids.append(f"REV-U-{hash_sig}")
        norm_df["id"] = ids

        # Reorder standard columns
        ordered_cols = [
            "id", "domain", "product_name", "sku_or_module", "batch_or_version",
            "channel", "rating", "raw_text", "created_at", "extra_metadata"
        ]
        norm_df = norm_df[ordered_cols]

        # Audit report
        sample_preview = norm_df.head(3).to_dict(orient="records")
        report = SchemaMappingReport(
            file_format=detected_format,
            total_raw_rows=total_rows,
            detected_columns=detected_mapping,
            unmapped_columns=unmapped_cols,
            column_confidence=confidences,
            rating_scale_detected=scale_desc,
            date_parsing_success_rate=round(date_rate, 4),
            preview_sample=sample_preview
        )

        return norm_df, report


# Singleton normalizer instance
schema_normalizer = SmartSchemaNormalizer()

__all__ = ["SmartSchemaNormalizer", "SchemaMappingReport", "schema_normalizer"]
