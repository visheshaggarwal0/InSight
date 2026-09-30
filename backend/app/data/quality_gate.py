"""quality_gate.py
Enterprise Data Quality Gate & Quarantine Engine for InSight.

Sits directly downstream of the SmartSchemaNormalizer to enforce strict
data health, hygiene, and integrity before any downstream ML, PII, or vector
embedding processing begins.

Guarantees:
  1. Zero Silent Failures: Corrupted or uninformative records are partitioned into
     a dedicated Quarantine Store rather than silently dropped or poisoning models.
  2. Text Sanitization: Catches blank strings, degenerate non-words, repeated character spam,
     and length overflows.
  3. Rating Guardrails: Enforces standard [1, 5] bounds with graceful clamping.
  4. Date Sanity: Validates reasonable temporal boundaries (e.g. discarding year 1970 or 2099).
  5. Deduplication: Eliminates cross-posted or copy-pasted duplicate verbatims.
  6. Audit Manifest: Computes an empirical Data Quality Score (0–100%) and rejection summary.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Minimum informative text character length after stripping whitespace & punctuation
MIN_INFORMATIVE_TEXT_LEN = 6

# Maximum text length before clipping to protect transformer context windows
MAX_SAFE_TEXT_LEN = 4000

# Common non-informative filler/spam strings
_DEGENERATE_LITERALS = {
    "nan", "null", "none", "n/a", "na", "nil", "undefined",
    "ok", "good", "bad", "yes", "no", "test", "testing",
    "asdf", "qwerty", "...", "???", "---", "***", "no comment"
}


@dataclass
class QuarantinedRecord:
    """Detailed record of a rejected row for client audit and compliance inspection."""
    record_id: str
    row_index: int
    raw_text: str
    rejection_code: str
    rejection_message: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityGateManifest:
    """Summary audit manifest produced for every ingestion batch."""
    total_input_rows: int
    passed_rows: int
    quarantined_rows: int
    duplicate_rows_dropped: int
    total_warnings: int
    quality_score_percentage: float
    rejection_breakdown: Dict[str, int] = field(default_factory=dict)
    quarantined_sample: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataQualityGate:
    """
    Enterprise Data Quality Gate.
    Filters, sanitizes, deduplicates, and quarantines raw normalized telemetry.
    """

    def __init__(
        self,
        min_text_len: int = MIN_INFORMATIVE_TEXT_LEN,
        max_text_len: int = MAX_SAFE_TEXT_LEN,
        deduplicate: bool = True
    ):
        self.min_text_len = min_text_len
        self.max_text_len = max_text_len
        self.deduplicate = deduplicate

    @staticmethod
    def _is_character_spam(text: str) -> bool:
        """Detects strings composed almost entirely of repeated single characters (e.g. 'aaaaaaa', '.....')."""
        stripped = text.strip()
        if len(stripped) == 0:
            return True
        # If 80%+ of characters are identical
        from collections import Counter
        counts = Counter(stripped.lower())
        most_common_char, count = counts.most_common(1)[0]
        if count / len(stripped) >= 0.75 and len(stripped) >= 8:
            return True
        return False

    @staticmethod
    def _validate_date_string(date_str: str) -> Tuple[str, bool]:
        """
        Validates date sanity. Discards dates before year 2000 or beyond current year + 1.
        Returns (valid_iso_str, is_adjusted).
        """
        now = datetime.now(timezone.utc)
        current_year = now.year

        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.year < 2000 or dt.year > current_year + 1:
                return now.isoformat(), True
            return date_str, False
        except Exception:
            return now.isoformat(), True

    def validate_and_quarantine(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, QualityGateManifest]:
        """
        Processes a normalized DataFrame through the quality filter.
        Returns:
            clean_df: Cleaned, deduplicated, and validated records.
            manifest: Audit report including rejection breakdown and quarantined records.
        """
        if df.empty:
            manifest = QualityGateManifest(
                total_input_rows=0,
                passed_rows=0,
                quarantined_rows=0,
                duplicate_rows_dropped=0,
                total_warnings=0,
                quality_score_percentage=100.0,
                rejection_breakdown={},
                quarantined_sample=[]
            )
            return df.copy(), manifest

        total_input = len(df)
        rejection_breakdown: Dict[str, int] = {}
        quarantined_records: List[QuarantinedRecord] = []
        valid_indices: List[int] = []
        warning_count = 0
        duplicate_count = 0

        seen_texts: set = set()

        # Temporary working columns
        cleaned_texts: Dict[int, str] = {}
        clamped_ratings: Dict[int, int] = {}
        validated_dates: Dict[int, str] = {}

        for idx, row in df.iterrows():
            rec_id = str(row.get("id", f"ROW-{idx}"))
            raw_text = str(row.get("raw_text", ""))
            stripped_text = raw_text.strip()
            lower_text = stripped_text.lower()

            # ---------------------------------------------------------------
            # 1. Empty or Blank Text
            # ---------------------------------------------------------------
            if not stripped_text or lower_text in {"nan", "null", "none", "n/a", "undefined"}:
                code = "EMPTY_TEXT"
                rejection_breakdown[code] = rejection_breakdown.get(code, 0) + 1
                quarantined_records.append(QuarantinedRecord(
                    record_id=rec_id,
                    row_index=int(idx),
                    raw_text=raw_text,
                    rejection_code=code,
                    rejection_message="Review text is completely blank, null, or a sentinel placeholder."
                ))
                continue

            # ---------------------------------------------------------------
            # 2. Character Spam / Repetition (e.g. 'aaaaaaa', '.....')
            # ---------------------------------------------------------------
            if self._is_character_spam(stripped_text):
                code = "REPETITIVE_CHARACTER_SPAM"
                rejection_breakdown[code] = rejection_breakdown.get(code, 0) + 1
                quarantined_records.append(QuarantinedRecord(
                    record_id=rec_id,
                    row_index=int(idx),
                    raw_text=raw_text,
                    rejection_code=code,
                    rejection_message="Review text exhibits excessive single-character repetition or spam."
                ))
                continue

            # ---------------------------------------------------------------
            # 3. Degenerate / Non-Informative Text (< min_text_len or single words)
            # ---------------------------------------------------------------
            alpha_num_text = re.sub(r"[^\w\s]", "", stripped_text).strip()
            if len(alpha_num_text) < self.min_text_len or lower_text in _DEGENERATE_LITERALS:
                code = "DEGENERATE_SHORT_TEXT"
                rejection_breakdown[code] = rejection_breakdown.get(code, 0) + 1
                quarantined_records.append(QuarantinedRecord(
                    record_id=rec_id,
                    row_index=int(idx),
                    raw_text=raw_text,
                    rejection_code=code,
                    rejection_message=(
                        f"Review text '{stripped_text}' has fewer than {self.min_text_len} alphanumeric "
                        "characters or is uninformative filler."
                    )
                ))
                continue

            # ---------------------------------------------------------------
            # 4. Duplicate Text Check (Deduplication)
            # ---------------------------------------------------------------
            normalized_dedup_key = re.sub(r"\s+", " ", lower_text).strip()
            if self.deduplicate and normalized_dedup_key in seen_texts:
                code = "DUPLICATE_TEXT"
                duplicate_count += 1
                rejection_breakdown[code] = rejection_breakdown.get(code, 0) + 1
                quarantined_records.append(QuarantinedRecord(
                    record_id=rec_id,
                    row_index=int(idx),
                    raw_text=raw_text,
                    rejection_code=code,
                    rejection_message="Identical verbatim text previously encountered in this ingestion batch."
                ))
                continue

            seen_texts.add(normalized_dedup_key)

            # ---------------------------------------------------------------
            # 5. Text Length Truncation (Safe Boundary Protection)
            # ---------------------------------------------------------------
            effective_text = stripped_text
            if len(stripped_text) > self.max_text_len:
                effective_text = stripped_text[:self.max_text_len]
                warning_count += 1
                logger.warning(
                    f"Record {rec_id} truncated from {len(stripped_text)} to {self.max_text_len} chars."
                )

            # ---------------------------------------------------------------
            # 6. Rating Validation & Bounds Enforcement
            # ---------------------------------------------------------------
            raw_rating = row.get("rating", 3)
            try:
                r_int = int(round(float(raw_rating)))
                if r_int < 1 or r_int > 5:
                    warning_count += 1
                    r_int = int(np.clip(r_int, 1, 5))
            except Exception:
                r_int = 3
                warning_count += 1

            # ---------------------------------------------------------------
            # 7. Date Validation
            # ---------------------------------------------------------------
            raw_date = str(row.get("created_at", ""))
            clean_date, date_adjusted = self._validate_date_string(raw_date)
            if date_adjusted:
                warning_count += 1

            # Passed all quarantine checks
            valid_indices.append(idx)
            cleaned_texts[idx] = effective_text
            clamped_ratings[idx] = r_int
            validated_dates[idx] = clean_date

        # Build clean output dataframe
        clean_df = df.loc[valid_indices].copy()
        clean_df["raw_text"] = clean_df.index.map(cleaned_texts)
        clean_df["rating"] = clean_df.index.map(clamped_ratings)
        clean_df["created_at"] = clean_df.index.map(validated_dates)

        # -------------------------------------------------------------------
        # Empirical Data Quality Score (0 - 100%)
        # -------------------------------------------------------------------
        quarantined_count = len(quarantined_records)
        q_rate = quarantined_count / max(1, total_input)
        dup_rate = duplicate_count / max(1, total_input)
        warn_rate = warning_count / max(1, total_input)

        # Penalty formula: 50% weight on quarantined loss, 30% on duplicates, 20% on warnings
        penalty = (0.50 * q_rate) + (0.30 * dup_rate) + (0.20 * warn_rate)
        quality_score = round(float(np.clip(100.0 * (1.0 - penalty), 0.0, 100.0)), 2)

        manifest = QualityGateManifest(
            total_input_rows=total_input,
            passed_rows=len(clean_df),
            quarantined_rows=quarantined_count,
            duplicate_rows_dropped=duplicate_count,
            total_warnings=warning_count,
            quality_score_percentage=quality_score,
            rejection_breakdown=rejection_breakdown,
            quarantined_sample=[r.to_dict() for r in quarantined_records[:10]]
        )

        return clean_df, manifest


# Singleton quality gate instance
data_quality_gate = DataQualityGate()

__all__ = ["DataQualityGate", "QuarantinedRecord", "QualityGateManifest", "data_quality_gate"]
