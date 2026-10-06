import hashlib
import json
import logging
import os
import re
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from app.core.pii import pii_redactor
from app.data.datasets import extract_complaint_span
from app.ml.drift import drift_detector
from app.ml.severity import classify_severity, corpus_negative_fraction

logger = logging.getLogger(__name__)

# SHA-256 of the committed sentiment artifact. joblib/pickle deserialisation
# executes arbitrary bytecode, so the artifact is verified before it is loaded.
# Override with INSIGHT_SENTIMENT_PIPELINE_SHA256 after any retrain.
SENTIMENT_PIPELINE_SHA256 = os.getenv(
    "INSIGHT_SENTIMENT_PIPELINE_SHA256",
    "db3786450839518ff8eac81146fe5b63b323723bbde6905b8dba83eb945427b0",
)


class RealDataLoader:
    """
    Production-grade real dataset loader and schema adapter for InSight.
    Loads real customer review telemetry (Sephora cosmetics dataset),
    applies offline ML models (TF-IDF + Logistic Regression sentiment pipeline,
    MiniLM semantic cluster assignments), sanitizes PII, and constructs
    backend-compatible review, theme, and drift artifacts without synthetic data.
    """

    DEFAULT_PROVISIONAL_THEMES = {
        0: "Eye Care & Dark Circles",
        1: "Facial Moisturizers & Dry Skin Hydration",
        2: "Acne, Breakouts & Skin Clearing Treatments",
        3: "Lip Care & Balms",
        4: "Fragrance, Scent & Sensory Properties",
        5: "Cleansers, Face Wash & Makeup Removal"
    }

    def __init__(self):
        self._find_base_dir()

    def _find_base_dir(self):
        """Resolves project root directory dynamically across local and container environments."""
        candidates = [
            os.environ.get("INSIGHT_ROOT"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
            os.getcwd(),
        ]
        self.base_dir = next((c for c in candidates if c and (os.path.exists(os.path.join(c, "data")) or os.path.exists(os.path.join(c, "outputs")))), candidates[1])

    def resolve_path(self, relative_path: str) -> str:
        """Resolves relative file paths against candidate project root locations."""
        candidates = [
            os.path.join(self.base_dir, relative_path),
            os.path.join(os.getcwd(), relative_path),
            os.path.join("..", relative_path),
            relative_path
        ]
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        raise FileNotFoundError(f"Artifact not found at relative path '{relative_path}'. Checked: {candidates}")

    def _sha256(self, path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _load_verified(self, pipeline_file: str):
        """
        Loads a joblib artifact only after an integrity check.

        ``joblib.load`` is ``pickle.load``: loading a repository-controlled file
        executes repository-controlled bytecode. When ``SENTIMENT_PIPELINE_SHA256``
        is configured the digest must match; otherwise the load is refused,
        because silently deserialising an unverified artifact is the vulnerability.
        """
        import joblib

        if not SENTIMENT_PIPELINE_SHA256:
            raise RuntimeError(
                "Refusing to deserialise the sentiment artifact without an integrity hash. "
                "Set INSIGHT_SENTIMENT_PIPELINE_SHA256 to the artifact's SHA-256, or convert "
                "the pipeline to ONNX and load it with onnxruntime (no code execution)."
            )

        actual = self._sha256(pipeline_file)
        if actual.lower() != SENTIMENT_PIPELINE_SHA256.strip().lower():
            raise RuntimeError(
                f"Sentiment artifact integrity check failed for {pipeline_file}: "
                f"expected {SENTIMENT_PIPELINE_SHA256}, got {actual}."
            )
        logger.info("Verified sentiment artifact SHA-256 before deserialisation.")
        return joblib.load(pipeline_file)

    def load_data(
        self,
        data_path: Optional[str] = None,
        sentiment_pipeline_path: Optional[str] = None,
        cluster_assignments_path: Optional[str] = None,
        cluster_representatives_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Loads the real Sephora 10k review dataset and transforms it into the backend schema.

        Returns:
            Dict containing:
                - 'reviews': List of review dictionaries matching backend API contract
                - 'themes': List of thematic cluster dictionaries with severity & sentiment distributions
                - 'drift_results': Temporal drift timeline and PSI stability analysis
                - 'row_count': Total valid processed reviews
        """
        # 1. Resolve paths
        # Note: data/ and outputs/ now live at the project root directly.
        # InSight_ML/ retains only its Python package files (*.py).
        csv_file = data_path or self.resolve_path("data/processed/cosmetics/cosmetics_10k.csv")
        pipeline_file = sentiment_pipeline_path or self.resolve_path("outputs/sentiment_baseline/sentiment_pipeline.joblib")
        assign_file = cluster_assignments_path or self.resolve_path("outputs/theme_detection/cluster_assignments.csv")
        rep_file = cluster_representatives_path or self.resolve_path("outputs/theme_detection/cluster_representatives.csv")

        # 2. Ingest raw dataset
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"Dataset file missing at: {csv_file}")
        
        df_raw = pd.read_csv(csv_file)
        required_raw_cols = ["review_text", "product_id", "product_name", "brand_name", "rating", "submission_time"]
        missing_cols = [c for c in required_raw_cols if c not in df_raw.columns]
        if missing_cols:
            raise ValueError(f"Dataset {csv_file} is missing required columns: {missing_cols}")

        # Drop any null or blank review texts safely
        df_raw = df_raw.dropna(subset=["review_text"]).copy()
        df_raw = df_raw[df_raw["review_text"].astype(str).str.strip().ne("")].copy()
        df_raw.reset_index(drop=True, inplace=True)
        total_rows = len(df_raw)

        # 3. Ingest and verify cluster assignments join
        if not os.path.exists(assign_file):
            raise FileNotFoundError(f"Cluster assignments artifact missing at: {assign_file}")
        
        df_assign = pd.read_csv(assign_file)
        if len(df_assign) != total_rows:
            raise ValueError(
                f"Row count mismatch between dataset ({total_rows}) and cluster assignments ({len(df_assign)}). "
                "Refusing to silently map misaligned clusters."
            )

        # Verify key consistency: check row_index, product_id, and review text alignment
        if "row_index" in df_assign.columns:
            index_aligned = (df_assign["row_index"].values == np.arange(total_rows)).all()
            if not index_aligned:
                raise ValueError("Cluster assignments row_index does not match consecutive integer range.")

        # Spot-check string similarity on first 100 rows to ensure exact 1-to-1 ordering
        sample_size = min(100, total_rows)
        raw_texts = df_raw["review_text"].head(sample_size).astype(str).values
        assign_texts = df_assign["review_text"].head(sample_size).astype(str).values
        if not (raw_texts == assign_texts).all():
            raise ValueError("Row alignment check failed: review_text in assignments does not match raw dataset order.")

        # 4. Ingest provisional themes and keywords
        theme_names = dict(self.DEFAULT_PROVISIONAL_THEMES)
        theme_keywords = {c: [] for c in range(6)}

        if os.path.exists(rep_file):
            df_rep = pd.read_csv(rep_file)
            for _, row in df_rep.drop_duplicates(subset=["cluster_id"]).iterrows():
                cid = int(row["cluster_id"])
                if "provisional_theme" in row and pd.notna(row["provisional_theme"]):
                    theme_names[cid] = str(row["provisional_theme"]).strip()
                if "top_keywords" in row and pd.notna(row["top_keywords"]):
                    theme_keywords[cid] = [kw.strip() for kw in str(row["top_keywords"]).split(",")]

        # 5. Offline sentiment model inference
        if not os.path.exists(pipeline_file):
            raise FileNotFoundError(f"Sentiment pipeline artifact missing at: {pipeline_file}")
        
        sentiment_pipeline = self._load_verified(pipeline_file)
        raw_reviews_list = df_raw["review_text"].astype(str).tolist()

        # predict + predict_proba in one pass: the TF-IDF transform dominates
        # cost and was previously being run twice over the full corpus.
        proba_matrix = sentiment_pipeline.predict_proba(raw_reviews_list)
        preds_raw = np.asarray(sentiment_pipeline.classes_)[proba_matrix.argmax(axis=1)]
        pipeline_classes = [str(c).lower() for c in sentiment_pipeline.classes_]

        # 6. Parse timestamps into quarterly cohorts (YYYY-Q#)
        submission_dates = pd.to_datetime(df_raw["submission_time"], errors="coerce")
        unparsed_dates = int(pd.isna(submission_dates).sum())
        if unparsed_dates:
            # Previously these were silently bucketed into "2021-Q1", which fed
            # the PSI timeline and could manufacture or mask a drift alert.
            logger.warning(
                "%d review(s) had an unparseable submission_time and are EXCLUDED from "
                "drift cohort assignment rather than assigned to a synthetic cohort.",
                unparsed_dates,
            )
        cohorts = [
            f"{dt.year}-Q{dt.quarter}" if pd.notna(dt) else None
            for dt in submission_dates
        ]

        # Real weak labels shipped with the Sephora corpus. These are the only
        # honest basis for evaluating sentiment on this dataset; the previous
        # code trained on the joblib model's own predictions and then scored
        # them against synthetic template text.
        weak_labels = None
        if "weak_sentiment" in df_raw.columns:
            weak_labels = df_raw["weak_sentiment"].astype(str).str.strip().str.lower().tolist()
        else:
            logger.warning(
                "Dataset has no 'weak_sentiment' column; sentiment governance metrics "
                "cannot be computed against real labels for this domain."
            )

        # 7. Build standardized review records
        cluster_ids = df_assign["minilm_cluster_k6"].values
        reviews = []

        for idx in range(total_rows):
            raw_text = raw_reviews_list[idx]
            sanitized_text, pii_tags = pii_redactor.redact(raw_text)

            pred_lower = str(preds_raw[idx]).lower()
            pred_upper = pred_lower.upper()

            # Previously an unknown label silently fell back to index 0
            # ("negative"), so a retrained model would report every confidence
            # as the negative probability.
            if pred_lower not in pipeline_classes:
                raise ValueError(
                    f"Sentiment model emitted label {pred_lower!r} which is absent from its "
                    f"own class list {pipeline_classes!r}. Refusing to guess a probability column."
                )
            cls_idx = pipeline_classes.index(pred_lower)
            confidence = round(float(proba_matrix[idx][cls_idx]), 4)

            c_id = int(cluster_ids[idx])
            title = theme_names.get(c_id, f"Theme Cluster {c_id}")

            product_name = str(df_raw["product_name"].iloc[idx])
            brand_name = str(df_raw["brand_name"].iloc[idx])
            product_id = str(df_raw["product_id"].iloc[idx])
            rating_val = int(df_raw["rating"].iloc[idx]) if pd.notna(df_raw["rating"].iloc[idx]) else 3
            cohort_str = cohorts[idx]
            weak_label = weak_labels[idx] if weak_labels else None

            review_id = f"REV-SEP-{idx:05d}"

            record = {
                "id": review_id,
                "domain": "d2c_cosmetics",
                "product_name": product_name,
                "brand_name": brand_name,
                "product_id": product_id,
                "sku_or_module": f"{brand_name} - {product_name}",
                "batch_or_version": cohort_str,
                "submission_date": (
                    submission_dates.iloc[idx].date().isoformat()
                    if pd.notna(submission_dates.iloc[idx]) else None
                ),
                "channel": "Sephora Online",
                "rating": rating_val,
                # Retained in server-side state ONLY. Never serialised into a
                # default API response; exposed solely through the role-gated
                # show_raw_pii path so compliance can re-identify a customer
                # for a safety recall.
                "raw_text": raw_text,
                "redacted_text": sanitized_text,
                "pii_detected": pii_tags,
                "sentiment_pred": pred_upper,
                "sentiment_confidence": confidence,
                "cluster_id": c_id,
                "theme_title": title,
                "highlight_span": extract_complaint_span(sanitized_text)
            }
            if weak_label in ("positive", "neutral", "negative"):
                record["ground_truth_label"] = weak_label.upper()
            reviews.append(record)

        # 8. Build aggregated themes
        theme_groups: Dict[int, List[Dict[str, Any]]] = {c: [] for c in range(6)}
        for r in reviews:
            theme_groups[r["cluster_id"]].append(r)

        baseline_neg = corpus_negative_fraction(reviews)

        themes = []
        for c_id in range(6):
            c_reviews = theme_groups[c_id]
            total_c = len(c_reviews)
            if total_c == 0:
                continue

            neg_count = sum(1 for r in c_reviews if r["sentiment_pred"] == "NEGATIVE")
            neu_count = sum(1 for r in c_reviews if r["sentiment_pred"] == "NEUTRAL")
            pos_count = sum(1 for r in c_reviews if r["sentiment_pred"] == "POSITIVE")
            neg_ratio = (neg_count / total_c) if total_c > 0 else 0.0

            p0_count = sum(
                1 for r in c_reviews
                if (r.get("highlight_span") or {}).get("detected") and (r.get("highlight_span") or {}).get("severity") == "P0"
            )
            p1_count = sum(
                1 for r in c_reviews
                if (r.get("highlight_span") or {}).get("detected") and (r.get("highlight_span") or {}).get("severity") == "P1"
            )
            max_prop_sev = "P0" if p0_count > 0 else ("P1" if p1_count > 0 else "P2")

            severity = classify_severity(
                neg_ratio,
                total_c,
                baseline_negative_fraction=baseline_neg,
                max_proposition_severity=max_prop_sev,
                p0_count=p0_count,
                p1_count=p1_count,
            )

            keywords = theme_keywords.get(c_id) or [kw.lower() for kw in theme_names[c_id].split() if len(kw) > 3][:5]

            # NOTE: raw_text is deliberately NOT included. Shipping unredacted
            # customer text inside /themes put raw PII in the browser before
            # any masking toggle was touched.
            sample_verbatims = [
                {
                    "id": r["id"],
                    "rating": r["rating"],
                    "text": r["redacted_text"],
                    "batch_or_version": r["batch_or_version"],
                    "sku_or_module": r["sku_or_module"],
                    "highlight_span": r["highlight_span"]
                }
                for r in c_reviews[:5]
            ]

            themes.append({
                "cluster_id": c_id,
                "title": theme_names[c_id],
                "keywords": keywords,
                "severity": severity,
                "review_count": total_c,
                "sentiment_distribution": {
                    "NEGATIVE": neg_count,
                    "NEUTRAL": neu_count,
                    "POSITIVE": pos_count
                },
                "negative_rate": round(neg_ratio * 100, 1),
                "sample_verbatims": sample_verbatims
            })

        themes.sort(key=lambda t: (t["severity"] == "CRITICAL", t["negative_rate"], t["review_count"]), reverse=True)

        # 9. Compute chronological drift results across quarterly cohorts.
        # Reviews with an unparseable submission_time carry batch_or_version=None
        # and are excluded from cohort analysis rather than forcing a value.
        dated_reviews = [r for r in reviews if r["batch_or_version"]]
        cohort_order = sorted({r["batch_or_version"] for r in dated_reviews})
        drift_results = drift_detector.analyze_drift_ordered(dated_reviews, cohort_order)

        # 10. Load sentence-level complaint clusters, feature requests, & praise clusters if available
        complaint_clusters = []
        feature_requests = []
        praise_clusters = []
        try:
            cc_path = self.resolve_path("outputs/pipeline_runs/complaint_clusters_latest.json")
            if os.path.exists(cc_path):
                with open(cc_path, "r", encoding="utf-8") as f:
                    cc_data = json.load(f)
                    complaint_clusters = cc_data.get("clusters", [])
        except Exception as exc:
            logger.info("Complaint clusters artifact not loaded: %s", exc)

        try:
            fr_path = self.resolve_path("outputs/pipeline_runs/feature_requests_latest.json")
            if os.path.exists(fr_path):
                with open(fr_path, "r", encoding="utf-8") as f:
                    fr_data = json.load(f)
                    feature_requests = fr_data.get("feature_requests", [])
        except Exception as exc:
            logger.info("Feature requests artifact not loaded: %s", exc)

        try:
            pc_path = self.resolve_path("outputs/pipeline_runs/praise_clusters_latest.json")
            if os.path.exists(pc_path):
                with open(pc_path, "r", encoding="utf-8") as f:
                    pc_data = json.load(f)
                    praise_clusters = pc_data.get("praise_clusters", pc_data.get("clusters", []))
        except Exception as exc:
            logger.info("Praise clusters artifact not loaded: %s", exc)

        try:
            rl_path = self.resolve_path("outputs/pipeline_runs/reviews_latest.json")
            if os.path.exists(rl_path):
                with open(rl_path, "r", encoding="utf-8") as f:
                    rl_data = json.load(f)
                    sents_map = {r["id"]: r.get("sentences", []) for r in rl_data if "id" in r and "sentences" in r}
                    for r in reviews:
                        if r["id"] in sents_map:
                            r["sentences"] = sents_map[r["id"]]
        except Exception as exc:
            logger.info("Reviews sentences artifact not loaded: %s", exc)

        for r in reviews:
            if "sentences" not in r:
                r["sentences"] = []

        # Return domain-isolated classifier without mutating global singletons
        from app.ml.sentiment import CalibratedSentimentClassifier
        sentiment_classifier = CalibratedSentimentClassifier()
        sentiment_classifier.pipeline = sentiment_pipeline
        sentiment_classifier.is_fitted = True

        return {
            "reviews": reviews,
            "themes": themes,
            "drift_results": drift_results,
            "complaint_clusters": complaint_clusters,
            "feature_requests": feature_requests,
            "praise_clusters": praise_clusters,
            "sentiment_model": sentiment_classifier,
            "row_count": total_rows,
            "reviews_without_cohort": len(reviews) - len(dated_reviews),
            "label_source": "weak_sentiment" if weak_labels else None,
        }

    def export_theme_centroids(
        self,
        embeddings_path: Optional[str] = None,
        assignments_path: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Computes and persists normalized centroids for the six MiniLM clusters.
        """
        emb_file = embeddings_path or self.resolve_path("outputs/theme_detection/minilm_embeddings.npy")
        assign_file = assignments_path or self.resolve_path("outputs/theme_detection/cluster_assignments.csv")
        out_file = output_path or os.path.join(self.base_dir, "outputs", "theme_detection", "theme_centroids.npy")

        embeddings = np.load(emb_file)
        df_assign = pd.read_csv(assign_file)

        if len(embeddings) != len(df_assign):
            raise ValueError("Embeddings count and assignments count do not match.")

        labels = df_assign["minilm_cluster_k6"].values
        centroids = []
        for c in range(int(labels.max()) + 1):
            mask = (labels == c)
            if not mask.any():
                logger.warning("Cluster %d has no members; skipping centroid.", c)
                continue
            c_mean = embeddings[mask].mean(axis=0)
            norm = float(np.linalg.norm(c_mean))
            # An empty/zero-norm slice previously produced NaN, which
            # np.maximum(norm, 1e-12) does NOT fix (NaN propagates), poisoning
            # every downstream similarity and emitting invalid JSON.
            if not np.isfinite(norm) or norm < 1e-12:
                logger.warning("Cluster %d centroid has degenerate norm %r; skipping.", c, norm)
                continue
            centroids.append(c_mean / norm)

        centroids_arr = np.array(centroids, dtype=np.float32)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        np.save(out_file, centroids_arr)
        return out_file

real_data_loader = RealDataLoader()
