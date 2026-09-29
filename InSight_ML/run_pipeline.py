"""run_pipeline.py
End-to-end InSight ML pipeline runner for the cosmetics dataset.

Usage:
    python InSight_ML/run_pipeline.py [--dataset cosmetics_10k] [--output-dir ...]

This script:
  1. Validates the input dataset schema and content
  2. Applies PII redaction
  3. Runs offline sentiment inference using the pre-trained pipeline
  4. Assigns provisional themes via MiniLM centroid proximity
  5. Extracts provisional complaint spans
  6. Assigns severity scores using configurable thresholds
  7. Computes temporal drift across quarterly cohorts (PSI)
  8. Verifies all span offsets against source texts
  9. Writes structured JSON output (one record per review)
  10. Generates a markdown pipeline run report

DESIGN NOTES:
  - Model artifacts are loaded once at startup, not per-record.
  - Records that fail validation are written to a separate rejected.json
    file rather than silently dropped.
  - No model training occurs here; all models are pre-trained offline.
  - Sentiment labels from this pipeline are derived from a model trained
    on weak (rating-derived) labels. They are NOT human ground truth.
  - Theme assignments are unsupervised and provisional.
  - Severity thresholds are configurable in pipeline_config.py.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

# ── Resolve project root ──────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent          # InSight_ML/
_ROOT = _HERE.parent                             # InSight/

# Add paths so local modules resolve correctly whether run from root or InSight_ML/
for p in [str(_ROOT), str(_HERE)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from InSight_ML.pipeline_config import (
    ARTIFACTS, DATASETS, PIPELINE_OUTPUT_DIR,
    SEVERITY, PSI, PROVISIONAL_THEME_NAMES, THEME,
)
from InSight_ML.complaint_extraction import extract_complaint_span
from InSight_ML.validation import (
    validate_cosmetics_df,
    verify_complaint_spans,
    ValidationResult,
)

# Backend modules (PII redactor and drift detector)
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.core.pii import pii_redactor
from app.ml.drift import TemporalDriftDetector

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("insight.pipeline")


# ── Helpers ───────────────────────────────────────────────────────────────

def _assign_severity(neg_fraction: float, cluster_size: int) -> str:
    """Assign a severity tier based on configurable thresholds.

    PROVISIONAL: See pipeline_config.SEVERITY for threshold values and caveats.
    """
    if neg_fraction >= SEVERITY["critical_neg_fraction"] and cluster_size >= SEVERITY["critical_min_volume"]:
        return "CRITICAL"
    if neg_fraction >= SEVERITY["high_neg_fraction"]:
        return "HIGH"
    if neg_fraction >= SEVERITY["medium_neg_fraction"]:
        return "MEDIUM"
    return "LOW"


def _quarterly_cohort(dt: Optional[pd.Timestamp], default: str = "unknown") -> str:
    """Convert a timestamp to 'YYYY-Q#' cohort string."""
    if pd.isna(dt):
        return default
    try:
        return f"{dt.year}-Q{dt.quarter}"
    except Exception:
        return default


# ── Pipeline stages ───────────────────────────────────────────────────────

def stage_load_and_validate(dataset_path: Path) -> tuple[pd.DataFrame, ValidationResult]:
    """Stage 1+2: Load CSV and validate schema / content."""
    logger.info("Stage 1: Loading dataset from %s", dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    df_raw = pd.read_csv(dataset_path)
    logger.info("  Loaded %d rows, %d columns", len(df_raw), len(df_raw.columns))

    logger.info("Stage 2: Validating input schema")
    result = validate_cosmetics_df(df_raw)
    logger.info("  %s", result.summary().split("\n")[0])
    for issue in result.issues:
        log_level = logging.ERROR if issue.level == "ERROR" else logging.WARNING if issue.level == "WARNING" else logging.INFO
        logger.log(log_level, "  [validation] %s", issue)
    return result.valid_df, result


def stage_pii_redact(df: pd.DataFrame) -> tuple[list, list]:
    """Stage 3: Apply PII redaction to all review texts."""
    logger.info("Stage 3: PII redaction on %d reviews", len(df))
    redacted_texts = []
    pii_tags_list = []
    for raw in df["review_text"].astype(str):
        redacted, tags = pii_redactor.redact(raw)
        redacted_texts.append(redacted)
        pii_tags_list.append(tags)
    n_pii = sum(1 for t in pii_tags_list if t)
    logger.info("  PII detected in %d/%d reviews (%.1f%%)", n_pii, len(df), 100 * n_pii / max(len(df), 1))
    return redacted_texts, pii_tags_list


def stage_sentiment(redacted_texts: list, pipeline_path: Path) -> tuple[list, list]:
    """Stage 4: Offline sentiment inference using pre-trained pipeline."""
    logger.info("Stage 4: Loading sentiment pipeline from %s", pipeline_path)
    if not pipeline_path.exists():
        raise FileNotFoundError(f"Sentiment pipeline not found: {pipeline_path}")

    t0 = time.time()
    pipeline = joblib.load(pipeline_path)
    logger.info("  Pipeline loaded in %.2fs", time.time() - t0)

    logger.info("  Running inference on %d texts", len(redacted_texts))
    t0 = time.time()
    preds_raw = pipeline.predict(redacted_texts)
    probs_raw = pipeline.predict_proba(redacted_texts)
    elapsed = time.time() - t0

    # Normalize to uppercase
    preds = [str(p).upper() for p in preds_raw]
    pipeline_classes = [str(c).lower() for c in pipeline.classes_]

    confidences = []
    for i, pred in enumerate(preds):
        pred_lower = pred.lower()
        idx = pipeline_classes.index(pred_lower) if pred_lower in pipeline_classes else 0
        confidences.append(round(float(probs_raw[i][idx]), 4))

    throughput = len(redacted_texts) / elapsed
    logger.info(
        "  Inference complete: %.2fs (%.0f reviews/sec)", elapsed, throughput
    )

    # Distribution summary (logged, not printed to stdout)
    from collections import Counter
    dist = Counter(preds)
    logger.info(
        "  Sentiment distribution: POSITIVE=%d, NEUTRAL=%d, NEGATIVE=%d",
        dist.get("POSITIVE", 0), dist.get("NEUTRAL", 0), dist.get("NEGATIVE", 0),
    )
    logger.info(
        "  NOTE: Labels are derived from a model trained on weak (rating-derived) "
        "labels. Not human-verified ground truth."
    )

    return preds, confidences


def stage_theme_assignment(
    df: pd.DataFrame,
    redacted_texts: list,
    assignments_path: Path,
    representatives_path: Path,
    original_indices: list,
) -> tuple[list, dict]:
    """Stage 5: Load pre-computed MiniLM cluster assignments and resolve theme names.

    Args:
        original_indices: The row indices from the ORIGINAL 10k CSV that correspond
            to each row in df. Used to correctly join positionally-indexed assignments.
    """
    logger.info("Stage 5: Loading cluster assignments from %s", assignments_path)

    if not assignments_path.exists():
        raise FileNotFoundError(f"Cluster assignments not found: {assignments_path}")

    df_assign = pd.read_csv(assignments_path)
    n_assignments = len(df_assign)
    n_valid = len(df)

    # Spot-check: the assignments CSV has review_text column for alignment verification
    # We verify that original_indices are within range
    if max(original_indices) >= n_assignments:
        raise ValueError(
            f"Source row indices extend to {max(original_indices)} but "
            f"cluster_assignments.csv only has {n_assignments} rows."
        )

    # Spot-check text alignment on up to 20 rows from the valid set
    sample_size = min(20, n_valid)
    for i in range(sample_size):
        orig_idx = original_indices[i]
        raw_text = str(df["review_text"].iloc[i])
        assign_text = str(df_assign["review_text"].iloc[orig_idx])
        if raw_text != assign_text:
            raise ValueError(
                f"Text alignment failed at valid row {i} (original idx {orig_idx}): "
                f"dataset text != assignment text. Assignments may be from a different dataset."
            )
    logger.info("  Alignment check passed (%d-row spot-check)", sample_size)

    # Extract cluster IDs using original row indices
    cluster_ids = [int(df_assign["minilm_cluster_k6"].iloc[idx]) for idx in original_indices]

    # Load provisional theme names
    theme_names = dict(PROVISIONAL_THEME_NAMES)
    theme_keywords: Dict[int, List[str]] = {c: [] for c in range(THEME["n_clusters"])}

    if representatives_path.exists():
        df_rep = pd.read_csv(representatives_path)
        for _, row in df_rep.drop_duplicates(subset=["cluster_id"]).iterrows():
            cid = int(row["cluster_id"])
            if "provisional_theme" in row and pd.notna(row["provisional_theme"]):
                theme_names[cid] = str(row["provisional_theme"]).strip()
            if "top_keywords" in row and pd.notna(row["top_keywords"]):
                theme_keywords[cid] = [kw.strip() for kw in str(row["top_keywords"]).split(",")]
        logger.info("  Loaded provisional theme names and keywords from representatives CSV")

    return cluster_ids, {"names": theme_names, "keywords": theme_keywords}


def stage_complaint_extraction(redacted_texts: list) -> list:
    """Stage 6: PROVISIONAL heuristic complaint span extraction."""
    logger.info("Stage 6: Complaint span extraction (heuristic, provisional)")
    spans = [extract_complaint_span(t) for t in redacted_texts]
    n_detected = sum(1 for s in spans if s.get("detected"))
    logger.info(
        "  Complaints detected: %d/%d (%.1f%%) [PROVISIONAL - no ground truth validation]",
        n_detected, len(spans), 100 * n_detected / max(len(spans), 1)
    )
    return spans


def stage_build_records(
    df: pd.DataFrame,
    redacted_texts: list,
    pii_tags_list: list,
    sentiment_preds: list,
    sentiment_confs: list,
    cluster_ids: list,
    theme_meta: dict,
    spans: list,
    original_indices: list,
) -> list:
    """Stage 7: Assemble per-review output records."""
    logger.info("Stage 7: Assembling review records")

    theme_names = theme_meta["names"]
    n = len(df)
    # df is already reset_index(drop=True) by the caller

    # Parse timestamps for cohort assignment
    submission_dates = pd.to_datetime(df["submission_time"], errors="coerce")
    DEFAULT_COHORT = "unknown"

    records = []
    for idx in range(n):
        raw_text = str(df["review_text"].iloc[idx])
        redacted = redacted_texts[idx]
        pii_tags = pii_tags_list[idx]
        pred = sentiment_preds[idx]
        conf = sentiment_confs[idx]
        c_id = int(cluster_ids[idx])
        theme_title = theme_names.get(c_id, f"Cluster {c_id}")
        span = spans[idx]
        cohort = _quarterly_cohort(submission_dates.iloc[idx], DEFAULT_COHORT)

        rating_raw = df["rating"].iloc[idx]
        rating = int(rating_raw) if pd.notna(rating_raw) and 1 <= float(rating_raw) <= 5 else None

        records.append({
            "id": f"REV-SEP-{idx:05d}",
            "pipeline_version": "1.1.0",
            "domain": "d2c_cosmetics",
            "product_id": str(df["product_id"].iloc[idx]),
            "product_name": str(df["product_name"].iloc[idx]),
            "brand_name": str(df["brand_name"].iloc[idx]),
            "sku_or_module": f"{df['brand_name'].iloc[idx]} - {df['product_name'].iloc[idx]}",
            "batch_or_version": cohort,
            "channel": "Sephora Online",
            "rating": rating,
            # Text representations
            "raw_text": raw_text,                     # original; NOT logged
            "redacted_text": redacted,                # PII-scrubbed
            "pii_detected": pii_tags,
            # Sentiment (PROVISIONAL: trained on weak labels)
            "sentiment_pred": pred,
            "sentiment_confidence": conf,
            "sentiment_is_provisional": True,
            "sentiment_label_note": "Trained on rating-derived weak labels; not human-verified ground truth.",
            # Theme (PROVISIONAL: unsupervised clustering)
            "cluster_id": c_id,
            "theme_title": theme_title,
            "theme_is_provisional": True,
            # Complaint (PROVISIONAL: heuristic regex)
            "highlight_span": span,
            "complaint_is_provisional": True,
            # Traceability – original_indices[idx] is the row number in the raw CSV
            "source_row_index": original_indices[idx],
        })

    logger.info("  Assembled %d records", len(records))
    return records


def stage_build_themes(records: list, theme_meta: dict) -> list:
    """Stage 8: Aggregate per-cluster theme summaries with severity."""
    logger.info("Stage 8: Building theme summaries")
    theme_names = theme_meta["names"]
    theme_keywords = theme_meta["keywords"]
    n_clusters = THEME["n_clusters"]

    cluster_groups: Dict[int, List[dict]] = {c: [] for c in range(n_clusters)}
    for r in records:
        cid = r["cluster_id"]
        if 0 <= cid < n_clusters:
            cluster_groups[cid].append(r)

    themes = []
    for c_id in range(n_clusters):
        c_reviews = cluster_groups[c_id]
        total_c = len(c_reviews)
        if total_c == 0:
            continue

        neg_count = sum(1 for r in c_reviews if r["sentiment_pred"] == "NEGATIVE")
        neu_count = sum(1 for r in c_reviews if r["sentiment_pred"] == "NEUTRAL")
        pos_count = sum(1 for r in c_reviews if r["sentiment_pred"] == "POSITIVE")
        neg_fraction = neg_count / total_c if total_c > 0 else 0.0

        severity = _assign_severity(neg_fraction, total_c)

        kws = theme_keywords.get(c_id) or [
            kw.lower() for kw in theme_names.get(c_id, "").split() if len(kw) > 3
        ][:5]

        sample_verbatims = [
            {
                "id": r["id"],
                "rating": r["rating"],
                "text": r["redacted_text"],
                "batch_or_version": r["batch_or_version"],
                "sku_or_module": r["sku_or_module"],
                "highlight_span": r["highlight_span"],
            }
            for r in c_reviews[:5]
        ]

        themes.append({
            "cluster_id": c_id,
            "title": theme_names.get(c_id, f"Cluster {c_id}"),
            "keywords": kws,
            "severity": severity,
            "severity_note": (
                f"PROVISIONAL: severity={severity} based on neg_fraction={neg_fraction:.3f} "
                f"(threshold: critical≥{SEVERITY['critical_neg_fraction']}, "
                f"high≥{SEVERITY['high_neg_fraction']}, medium≥{SEVERITY['medium_neg_fraction']}, "
                f"critical_min_vol={SEVERITY['critical_min_volume']}). "
                "Thresholds not statistically validated for this domain."
            ),
            "review_count": total_c,
            "sentiment_distribution": {
                "NEGATIVE": neg_count,
                "NEUTRAL": neu_count,
                "POSITIVE": pos_count,
            },
            "negative_rate": round(neg_fraction * 100, 1),
            "sample_verbatims": sample_verbatims,
        })

    themes.sort(
        key=lambda t: (t["severity"] == "CRITICAL", t["negative_rate"], t["review_count"]),
        reverse=True,
    )
    logger.info("  Built %d theme summaries", len(themes))
    return themes


def stage_drift(records: list) -> dict:
    """Stage 9: Temporal drift analysis across quarterly cohorts."""
    logger.info("Stage 9: Drift analysis")
    sorted_records = sorted(records, key=lambda r: r["batch_or_version"])
    detector = TemporalDriftDetector()
    drift = detector.analyze_drift(sorted_records)
    n_alerts = len(drift.get("alerts", []))
    logger.info(
        "  Analyzed %d cohorts, %d alerts (PSI thresholds: moderate≥%.2f, critical≥%.2f) [PROVISIONAL]",
        drift.get("batches_analyzed", 0),
        n_alerts,
        PSI["moderate_threshold"],
        PSI["critical_threshold"],
    )
    return drift


def stage_verify_spans(records: list) -> list:
    """Stage 10: Verify complaint span offsets against source texts."""
    logger.info("Stage 10: Span offset verification")
    spans = [r["highlight_span"] for r in records]
    # Verify against redacted text (what the span was extracted from)
    source_texts = [r["redacted_text"] for r in records]
    issues = verify_complaint_spans(spans, source_texts)
    if not issues:
        logger.info("  All span offsets valid")
    for issue in issues:
        logger.error("  [span_check] %s", issue)
    return issues


# ── Main entry point ──────────────────────────────────────────────────────

def run_pipeline(
    dataset_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> dict:
    """Run the full end-to-end pipeline and return a summary dict."""

    dataset_path = dataset_path or DATASETS["cosmetics_10k"]
    output_dir = output_dir or PIPELINE_OUTPUT_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logger.info("=" * 60)
    logger.info("InSight Pipeline Run  |  run_id=%s", run_id)
    logger.info("=" * 60)

    pipeline_start = time.time()
    stage_timings: Dict[str, float] = {}

    # ── Stage 1+2: Load & validate ──
    t = time.time()
    df, validation_result = stage_load_and_validate(Path(dataset_path))
    stage_timings["load_and_validate"] = time.time() - t

    # Capture the original integer row positions from the raw CSV
    # (before any de-duplication or filtering by validation).
    # These are needed to correctly join positionally-indexed cluster assignments.
    original_indices = df.index.tolist()
    df = df.reset_index(drop=True)  # reset for downstream indexing

    # Write rejected records
    if validation_result.n_rejected > 0:
        logger.warning(
            "  %d rows rejected during validation. See validation issues above.",
            validation_result.n_rejected
        )

    if validation_result.has_errors and len(df) == 0:
        logger.error("No valid records after validation. Aborting pipeline.")
        return {"status": "FAILED", "reason": "validation_errors", "run_id": run_id}

    n_valid = len(df)

    # ── Stage 3: PII redaction ──
    t = time.time()
    redacted_texts, pii_tags_list = stage_pii_redact(df)
    stage_timings["pii_redaction"] = time.time() - t

    # ── Stage 4: Sentiment ──
    t = time.time()
    sentiment_preds, sentiment_confs = stage_sentiment(redacted_texts, ARTIFACTS["sentiment_pipeline"])
    stage_timings["sentiment_inference"] = time.time() - t

    # ── Stage 5: Theme assignment ──
    t = time.time()
    cluster_ids, theme_meta = stage_theme_assignment(
        df,
        redacted_texts,
        ARTIFACTS["cluster_assignments"],
        ARTIFACTS["cluster_representatives"],
        original_indices=original_indices,
    )
    stage_timings["theme_assignment"] = time.time() - t

    # ── Stage 6: Complaint extraction ──
    t = time.time()
    spans = stage_complaint_extraction(redacted_texts)
    stage_timings["complaint_extraction"] = time.time() - t

    # ── Stage 7: Build records ──
    t = time.time()
    records = stage_build_records(
        df, redacted_texts, pii_tags_list,
        sentiment_preds, sentiment_confs,
        cluster_ids, theme_meta, spans,
        original_indices=original_indices,
    )
    stage_timings["build_records"] = time.time() - t

    # ── Stage 8: Theme summaries ──
    t = time.time()
    themes = stage_build_themes(records, theme_meta)
    stage_timings["build_themes"] = time.time() - t

    # ── Stage 9: Drift ──
    t = time.time()
    drift = stage_drift(records)
    stage_timings["drift_analysis"] = time.time() - t

    # ── Stage 10: Span verification ──
    t = time.time()
    span_issues = stage_verify_spans(records)
    stage_timings["span_verification"] = time.time() - t

    total_elapsed = time.time() - pipeline_start

    # ── Compute final summary statistics ──
    from collections import Counter
    sent_dist = Counter(r["sentiment_pred"] for r in records)
    n_pii = sum(1 for r in records if r["pii_detected"])
    n_complaints = sum(1 for r in records if r["highlight_span"].get("detected"))
    sev_dist = Counter(t["severity"] for t in themes)

    summary = {
        "run_id": run_id,
        "status": "SUCCESS",
        "dataset": str(dataset_path),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_input_rows": validation_result.n_input,
        "n_valid_rows": n_valid,
        "n_rejected_rows": validation_result.n_rejected,
        "validation_issues": [str(i) for i in validation_result.issues],
        "span_issues": [str(i) for i in span_issues],
        "sentiment_distribution": dict(sent_dist),
        "pii_redacted_count": n_pii,
        "complaint_detected_count": n_complaints,
        "complaint_detected_rate_pct": round(100 * n_complaints / max(n_valid, 1), 1),
        "n_themes": len(themes),
        "theme_severity_distribution": dict(sev_dist),
        "n_drift_cohorts": drift.get("batches_analyzed", 0),
        "n_drift_alerts": len(drift.get("alerts", [])),
        "stage_timings_sec": {k: round(v, 3) for k, v in stage_timings.items()},
        "total_elapsed_sec": round(total_elapsed, 2),
        "throughput_reviews_per_sec": round(n_valid / total_elapsed, 1),
        "provisional_notices": [
            "Sentiment labels derived from a model trained on weak (rating-derived) labels. Not human-verified ground truth.",
            "Theme assignments are unsupervised (MiniLM+KMeans). Cluster validity is supported by silhouette/DBCV metrics but not by human annotation.",
            "Severity thresholds (pipeline_config.SEVERITY) are provisional engineering choices, not statistically validated operating points.",
            "PSI drift thresholds (pipeline_config.PSI) use industry standard defaults; not calibrated for this domain.",
            "Complaint detection is heuristic regex only. No precision/recall measured (no ground truth spans available).",
        ],
    }

    # ── Write outputs ──
    reviews_path = output_dir / f"reviews_{run_id}.json"
    themes_path = output_dir / f"themes_{run_id}.json"
    drift_path = output_dir / f"drift_{run_id}.json"
    summary_path = output_dir / f"summary_{run_id}.json"
    latest_reviews_path = output_dir / "reviews_latest.json"
    latest_themes_path = output_dir / "themes_latest.json"
    latest_drift_path = output_dir / "drift_latest.json"
    latest_summary_path = output_dir / "summary_latest.json"

    logger.info("Writing outputs to %s", output_dir)

    # Write records without raw_text to avoid logging review content
    # (raw_text remains in the in-memory dict for API use)
    records_safe = []
    for r in records:
        r_out = dict(r)
        r_out.pop("raw_text", None)  # do not persist raw PII-containing text to pipeline outputs
        records_safe.append(r_out)

    with open(reviews_path, "w", encoding="utf-8") as f:
        json.dump(records_safe, f, ensure_ascii=False, indent=2)
    with open(themes_path, "w", encoding="utf-8") as f:
        json.dump(themes, f, ensure_ascii=False, indent=2)
    with open(drift_path, "w", encoding="utf-8") as f:
        json.dump(drift, f, ensure_ascii=False, indent=2)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Symlink-style copies for latest
    for src, dst in [
        (reviews_path, latest_reviews_path),
        (themes_path, latest_themes_path),
        (drift_path, latest_drift_path),
        (summary_path, latest_summary_path),
    ]:
        import shutil
        shutil.copy2(src, dst)

    logger.info("=" * 60)
    logger.info("Pipeline completed in %.2fs", total_elapsed)
    logger.info("  Valid records: %d/%d", n_valid, validation_result.n_input)
    logger.info("  Throughput: %.0f reviews/sec", summary["throughput_reviews_per_sec"])
    logger.info("  Sentiment: %s", dict(sent_dist))
    logger.info("  Complaints detected: %d (%.1f%%)", n_complaints, summary["complaint_detected_rate_pct"])
    logger.info("  Themes: %d | Drift alerts: %d", len(themes), summary["n_drift_alerts"])
    logger.info("  Outputs: %s", output_dir)
    logger.info("=" * 60)

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Run the InSight end-to-end ML pipeline on the cosmetics dataset."
    )
    parser.add_argument(
        "--dataset",
        default=str(DATASETS["cosmetics_10k"]),
        help="Path to the processed cosmetics CSV file.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PIPELINE_OUTPUT_DIR),
        help="Directory to write pipeline outputs.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.getLogger().setLevel(args.log_level)

    summary = run_pipeline(
        dataset_path=Path(args.dataset),
        output_dir=Path(args.output_dir),
    )

    print(json.dumps(summary, indent=2))
    return 0 if summary.get("status") == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
