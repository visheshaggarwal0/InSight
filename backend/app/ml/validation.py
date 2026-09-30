"""validation.py
Input schema validation for the InSight ML pipeline.

Validates DataFrames before they enter the processing pipeline.
Every validation failure is collected and reported; records that fail
critical checks are quarantined and excluded from further processing
rather than silently dropped or propagated with bad data.

All functions return a ValidationResult dataclass containing:
  - valid_df   : the cleaned, valid subset of the input
  - issues     : list of Issue objects describing every problem found
  - n_input    : number of input rows
  - n_valid    : number of rows that passed validation
  - n_rejected : number of rows rejected (n_input - n_valid)
"""

from __future__ import annotations

import logging
import numbers
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    """A single validation finding."""
    level: str          # 'ERROR' | 'WARNING' | 'INFO'
    check: str          # machine-readable check name
    message: str        # human-readable description
    n_affected: int = 0 # number of rows affected

    def __str__(self) -> str:
        return f"[{self.level}] {self.check}: {self.message} (rows affected: {self.n_affected})"


ValidationIssue = Issue  # Alias for backward-compatibility


@dataclass
class ValidationResult:
    valid_df: pd.DataFrame
    issues: List[Issue] = field(default_factory=list)
    n_input: int = 0
    n_valid: int = 0
    n_rejected: int = 0

    @property
    def has_errors(self) -> bool:
        return any(i.level == "ERROR" for i in self.issues)

    def summary(self) -> str:
        lines = [
            f"Validation summary: {self.n_valid}/{self.n_input} rows accepted, "
            f"{self.n_rejected} rejected."
        ]
        for issue in self.issues:
            lines.append(f"  {issue}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cosmetics dataset validator
# ---------------------------------------------------------------------------

COSMETICS_REQUIRED_COLS = [
    "review_text",
    "product_id",
    "product_name",
    "brand_name",
    "rating",
    "submission_time",
]

COSMETICS_OPTIONAL_COLS = [
    "weak_sentiment",
    "review_title",
    "is_recommended",
    "helpfulness",
    "total_feedback_count",
    "total_neg_feedback_count",
    "total_pos_feedback_count",
    "price_usd",
    "primary_category",
    "secondary_category",
    "tertiary_category",
    "loves_count",
    "word_count",
]


def validate_cosmetics_df(df: pd.DataFrame) -> ValidationResult:
    """Validate the cosmetics_10k dataset before pipeline ingestion.

    Checks:
      1. Required columns present
      2. No completely empty review_text
      3. rating within [1, 5]
      4. Duplicate review_text detection (warning, not rejection)
      5. submission_time parseable
      6. weak_sentiment values in expected set (if column present)
    """
    issues: List[Issue] = []
    n_input = len(df)

    # 1. Required columns
    missing_cols = [c for c in COSMETICS_REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        issues.append(Issue(
            level="ERROR",
            check="missing_required_columns",
            message=f"Required columns absent: {missing_cols}",
            n_affected=n_input,
        ))
        return ValidationResult(
            valid_df=df.head(0),  # empty
            issues=issues,
            n_input=n_input,
            n_valid=0,
            n_rejected=n_input,
        )

    # Unexpected columns (informational)
    expected_cols = set(COSMETICS_REQUIRED_COLS + COSMETICS_OPTIONAL_COLS)
    unexpected = [c for c in df.columns if c not in expected_cols]
    if unexpected:
        issues.append(Issue(
            level="INFO",
            check="unexpected_columns",
            message=f"Unexpected columns (will be passed through): {unexpected}",
        ))

    mask_valid = pd.Series(True, index=df.index)

    # 2. Empty review text
    null_text = df["review_text"].isna() | (df["review_text"].astype(str).str.strip() == "")
    n_null = null_text.sum()
    if n_null > 0:
        issues.append(Issue(
            level="ERROR",
            check="empty_review_text",
            message=f"{n_null} rows have null or blank review_text and will be excluded.",
            n_affected=int(n_null),
        ))
        mask_valid &= ~null_text

    # 3. Rating range
    coerced_columns: List[str] = []
    if "rating" in df.columns:
        numeric_rating = pd.to_numeric(df["rating"], errors="coerce")
        bad_rating = mask_valid & (numeric_rating.isna() | (numeric_rating < 1) | (numeric_rating > 5))
        n_bad = bad_rating.sum()
        if n_bad > 0:
            issues.append(Issue(
                level="WARNING",
                check="invalid_rating_range",
                message=f"{n_bad} rows have rating outside [1,5]. Rating coerced to NaN → will be treated as missing.",
                n_affected=int(n_bad),
            ))
        # The report above promises the coercion; perform it on the RETURNED
        # frame so downstream consumers never see a non-numeric rating string
        # (e.g. "N/A") that would crash a numeric coercion downstream.
        coerced_columns.append("rating")

    # 4. Duplicates (warning only – keep first occurrence)
    dup_mask = df.duplicated(subset=["review_text"], keep="first")
    n_dup = dup_mask.sum()
    if n_dup > 0:
        issues.append(Issue(
            level="WARNING",
            check="duplicate_review_text",
            message=f"{n_dup} duplicate review_text values detected. Keeping first occurrence.",
            n_affected=int(n_dup),
        ))
        # De-duplicate among VALID rows only. Computing duplicates over the full
        # frame would drop a later VALID copy whenever the FIRST occurrence was
        # already masked out (blank/invalid), losing the only usable text.
        dup_in_valid = pd.Series(False, index=df.index)
        dup_in_valid.loc[mask_valid] = df.loc[mask_valid].duplicated(
            subset=["review_text"], keep="first"
        )
        mask_valid &= ~dup_in_valid

    # 5. submission_time parseable
    parsed_dates = pd.to_datetime(df.loc[mask_valid, "submission_time"], errors="coerce")
    n_bad_date = parsed_dates.isna().sum()
    if n_bad_date > 0:
        issues.append(Issue(
            level="WARNING",
            check="unparseable_submission_time",
            message=(
                f"{n_bad_date} rows have unparseable submission_time. "
                "These will receive a default cohort label."
            ),
            n_affected=int(n_bad_date),
        ))

    # 6. weak_sentiment values
    if "weak_sentiment" in df.columns:
        valid_sentiments = {"positive", "neutral", "negative"}
        sentinel_values = df.loc[mask_valid, "weak_sentiment"].dropna().astype(str).str.lower()
        bad_sent = sentinel_values[~sentinel_values.isin(valid_sentiments)]
        if len(bad_sent) > 0:
            issues.append(Issue(
                level="WARNING",
                check="unexpected_weak_sentiment_values",
                message=f"{len(bad_sent)} rows have unexpected weak_sentiment values: {bad_sent.unique().tolist()}",
                n_affected=len(bad_sent),
            ))

    valid_df = df[mask_valid].copy()
    for col in coerced_columns:
        if col in valid_df.columns:
            valid_df[col] = pd.to_numeric(valid_df[col], errors="coerce")
    n_valid = len(valid_df)
    n_rejected = n_input - n_valid

    return ValidationResult(
        valid_df=valid_df,
        issues=issues,
        n_input=n_input,
        n_valid=n_valid,
        n_rejected=n_rejected,
    )


# ---------------------------------------------------------------------------
# Generic CSV upload validator
# ---------------------------------------------------------------------------

def validate_custom_csv(df: pd.DataFrame, text_col: str, rating_col: Optional[str] = None) -> ValidationResult:
    """Validate a user-uploaded CSV before processing.

    Args:
        df: The parsed DataFrame.
        text_col: Column name containing review text.
        rating_col: Optional column name containing numeric rating.

    Returns:
        ValidationResult with cleaned DataFrame and issue list.
    """
    issues: List[Issue] = []
    n_input = len(df)

    if text_col not in df.columns:
        issues.append(Issue(
            level="ERROR",
            check="text_column_missing",
            message=f"Text column '{text_col}' not found in uploaded CSV.",
            n_affected=n_input,
        ))
        return ValidationResult(
            valid_df=df.head(0),
            issues=issues,
            n_input=n_input,
            n_valid=0,
            n_rejected=n_input,
        )

    mask_valid = pd.Series(True, index=df.index)

    # Empty texts
    null_text = df[text_col].isna() | (df[text_col].astype(str).str.strip() == "")
    n_null = null_text.sum()
    if n_null > 0:
        issues.append(Issue(
            level="ERROR",
            check="empty_review_text",
            message=f"{n_null} rows have empty or null text and will be excluded.",
            n_affected=int(n_null),
        ))
        mask_valid &= ~null_text

    # Minimum viable text length (< 5 chars after strip)
    too_short = mask_valid & (df[text_col].astype(str).str.strip().str.len() < 5)
    n_short = too_short.sum()
    if n_short > 0:
        issues.append(Issue(
            level="WARNING",
            check="very_short_review_text",
            message=f"{n_short} rows have fewer than 5 characters after stripping. These may produce unreliable predictions.",
            n_affected=int(n_short),
        ))

    # Duplicates
    dup_mask = df.duplicated(subset=[text_col], keep="first")
    n_dup = dup_mask.sum()
    if n_dup > 0:
        issues.append(Issue(
            level="WARNING",
            check="duplicate_review_text",
            message=f"{n_dup} duplicate texts detected. Keeping first occurrence.",
            n_affected=int(n_dup),
        ))
        # De-duplicate among VALID rows only (see validate_cosmetics_df).
        dup_in_valid = pd.Series(False, index=df.index)
        dup_in_valid.loc[mask_valid] = df.loc[mask_valid].duplicated(
            subset=[text_col], keep="first"
        )
        mask_valid &= ~dup_in_valid

    # Rating range
    coerced_columns: List[str] = []
    if rating_col and rating_col in df.columns:
        numeric_rating = pd.to_numeric(df[rating_col], errors="coerce")
        bad_rating = mask_valid & numeric_rating.notna() & ((numeric_rating < 1) | (numeric_rating > 5))
        n_bad = bad_rating.sum()
        if n_bad > 0:
            issues.append(Issue(
                level="WARNING",
                check="invalid_rating_range",
                message=f"{n_bad} rows have rating outside [1,5].",
                n_affected=int(n_bad),
            ))
        # Apply the coercion to the returned frame (not just a local) so
        # downstream numeric consumers cannot crash on a string like "N/A".
        coerced_columns.append(rating_col)

    valid_df = df[mask_valid].copy()
    for col in coerced_columns:
        if col in valid_df.columns:
            valid_df[col] = pd.to_numeric(valid_df[col], errors="coerce")
    n_valid = len(valid_df)
    n_rejected = n_input - n_valid

    return ValidationResult(
        valid_df=valid_df,
        issues=issues,
        n_input=n_input,
        n_valid=n_valid,
        n_rejected=n_rejected,
    )


# ---------------------------------------------------------------------------
# Span offset verifier (used after complaint extraction)
# ---------------------------------------------------------------------------

def verify_complaint_spans(
    spans: List[dict],
    source_texts: List[str],
) -> List[Issue]:
    """Verify that all detected complaint spans have valid offsets.

    For each span where detected=True, checks that:
      - start and end are integers
      - 0 <= start < end <= len(source_text)
      - source_text[start:end] == span['text']

    Returns a list of Issue objects for any failures.
    """
    issues: List[Issue] = []
    n_invalid_offset = 0
    n_text_mismatch = 0

    # A length mismatch would silently validate only the zip() prefix, hiding
    # unchecked spans. Fail loudly instead.
    if len(spans) != len(source_texts):
        raise ValueError(
            f"verify_complaint_spans: spans/source_texts length mismatch "
            f"({len(spans)} spans vs {len(source_texts)} source texts). "
            "Refusing to silently verify only the overlapping prefix."
        )

    for i, (span, src) in enumerate(zip(spans, source_texts)):
        if not span.get("detected"):
            continue

        start = span.get("start")
        end = span.get("end")
        span_text = span.get("text", "")

        # Offset type and range. numbers.Integral covers numpy.int64 offsets
        # (which is what a pandas-derived offset is) as well as plain ints.
        if not (
            isinstance(start, numbers.Integral)
            and isinstance(end, numbers.Integral)
        ):
            n_invalid_offset += 1
            continue
        if not (0 <= start < end <= len(src)):
            n_invalid_offset += 1
            continue

        # Exact string match
        if src[start:end] != span_text:
            n_text_mismatch += 1

    if n_invalid_offset > 0:
        issues.append(Issue(
            level="ERROR",
            check="invalid_span_offsets",
            message=f"{n_invalid_offset} detected spans have offsets outside valid range.",
            n_affected=n_invalid_offset,
        ))
    if n_text_mismatch > 0:
        issues.append(Issue(
            level="ERROR",
            check="span_text_offset_mismatch",
            message=(
                f"{n_text_mismatch} detected spans have text that does not match "
                "source_text[start:end]. This indicates a post-processing text mutation."
            ),
            n_affected=n_text_mismatch,
        ))

    return issues
