import os
import re
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
import joblib

from app.core.pii import pii_redactor
from app.data.datasets import extract_complaint_span
from app.ml.drift import drift_detector

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
        self.base_dir = next((c for c in candidates if c and (os.path.exists(os.path.join(c, "data")) or os.path.exists(os.path.join(c, "InSight_ML")))), candidates[1])

    def resolve_path(self, relative_path: str) -> str:
        """Resolves relative file paths against candidate project root locations."""
        alt_rel = relative_path.replace("InSight_ML/", "") if relative_path.startswith("InSight_ML/") else f"InSight_ML/{relative_path}"
        candidates = [
            os.path.join(self.base_dir, relative_path),
            os.path.join(self.base_dir, alt_rel),
            os.path.join(os.getcwd(), relative_path),
            os.path.join(os.getcwd(), alt_rel),
            os.path.join("..", relative_path),
            relative_path
        ]
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        raise FileNotFoundError(f"Artifact not found at relative path '{relative_path}'. Checked: {candidates}")

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
        csv_file = data_path or self.resolve_path("InSight_ML/data/processed/cosmetics/cosmetics_10k.csv")
        pipeline_file = sentiment_pipeline_path or self.resolve_path("InSight_ML/outputs/sentiment_baseline/sentiment_pipeline.joblib")
        assign_file = cluster_assignments_path or self.resolve_path("InSight_ML/outputs/theme_detection/cluster_assignments.csv")
        rep_file = cluster_representatives_path or self.resolve_path("InSight_ML/outputs/theme_detection/cluster_representatives.csv")

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
        
        sentiment_pipeline = joblib.load(pipeline_file)
        raw_reviews_list = df_raw["review_text"].astype(str).tolist()
        
        preds_raw = sentiment_pipeline.predict(raw_reviews_list)
        probs_raw = sentiment_pipeline.predict_proba(raw_reviews_list)
        pipeline_classes = [str(c).lower() for c in sentiment_pipeline.classes_]

        # 6. Parse timestamps into quarterly cohorts (YYYY-Q#)
        submission_dates = pd.to_datetime(df_raw["submission_time"], errors="coerce")
        default_cohort = "2021-Q1"
        cohorts = []
        for dt in submission_dates:
            if pd.notna(dt):
                cohorts.append(f"{dt.year}-Q{dt.quarter}")
            else:
                cohorts.append(default_cohort)

        # 7. Build standardized review records
        cluster_ids = df_assign["minilm_cluster_k6"].values
        reviews = []

        for idx in range(total_rows):
            raw_text = raw_reviews_list[idx]
            sanitized_text, pii_tags = pii_redactor.redact(raw_text)

            pred_lower = str(preds_raw[idx]).lower()
            pred_upper = pred_lower.upper()

            cls_idx = pipeline_classes.index(pred_lower) if pred_lower in pipeline_classes else 0
            confidence = round(float(probs_raw[idx][cls_idx]), 4)

            c_id = int(cluster_ids[idx])
            title = theme_names.get(c_id, f"Theme Cluster {c_id}")

            product_name = str(df_raw["product_name"].iloc[idx])
            brand_name = str(df_raw["brand_name"].iloc[idx])
            product_id = str(df_raw["product_id"].iloc[idx])
            rating_val = int(df_raw["rating"].iloc[idx]) if pd.notna(df_raw["rating"].iloc[idx]) else 3
            cohort_str = cohorts[idx]

            review_id = f"REV-SEP-{idx:05d}"

            reviews.append({
                "id": review_id,
                "domain": "d2c_cosmetics",
                "product_name": product_name,
                "brand_name": brand_name,
                "product_id": product_id,
                "sku_or_module": f"{brand_name} - {product_name}",
                "batch_or_version": cohort_str,
                "channel": "Sephora Online",
                "rating": rating_val,
                "raw_text": raw_text,
                "redacted_text": sanitized_text,
                "pii_detected": pii_tags,
                "sentiment_pred": pred_upper,
                "sentiment_confidence": confidence,
                "cluster_id": c_id,
                "theme_title": title,
                "highlight_span": extract_complaint_span(sanitized_text)
            })

        # 8. Build aggregated themes
        theme_groups: Dict[int, List[Dict[str, Any]]] = {c: [] for c in range(6)}
        for r in reviews:
            theme_groups[r["cluster_id"]].append(r)

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

            if neg_ratio > 0.35:
                severity = "CRITICAL" if total_c > 500 else "HIGH"
            elif neg_ratio > 0.20:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            keywords = theme_keywords.get(c_id) or [kw.lower() for kw in theme_names[c_id].split() if len(kw) > 3][:5]

            sample_verbatims = [
                {
                    "id": r["id"],
                    "rating": r["rating"],
                    "text": r["redacted_text"],
                    "raw_text": r["raw_text"],
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

        # 9. Compute chronological drift results across quarterly cohorts
        sorted_reviews = sorted(reviews, key=lambda r: r["batch_or_version"])
        drift_results = drift_detector.analyze_drift(sorted_reviews)

        return {
            "reviews": reviews,
            "themes": themes,
            "drift_results": drift_results,
            "row_count": total_rows
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
        emb_file = embeddings_path or self.resolve_path("InSight_ML/outputs/theme_detection/minilm_embeddings.npy")
        assign_file = assignments_path or self.resolve_path("InSight_ML/outputs/theme_detection/cluster_assignments.csv")
        out_file = output_path or os.path.join(self.base_dir, "InSight_ML", "outputs", "theme_detection", "theme_centroids.npy")

        embeddings = np.load(emb_file)
        df_assign = pd.read_csv(assign_file)

        if len(embeddings) != len(df_assign):
            raise ValueError("Embeddings count and assignments count do not match.")

        labels = df_assign["minilm_cluster_k6"].values
        centroids = []
        for c in range(6):
            mask = (labels == c)
            c_mean = embeddings[mask].mean(axis=0)
            c_norm = c_mean / np.linalg.norm(c_mean)
            centroids.append(c_norm)

        centroids_arr = np.array(centroids, dtype=np.float32)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        np.save(out_file, centroids_arr)
        return out_file

real_data_loader = RealDataLoader()
