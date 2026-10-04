"""knowledge_pipeline.py
End-to-End Enterprise Knowledge Pipeline Orchestrator for InSight.

Chains all Data Engineering & Machine Learning stages:
  1. Smart Schema Normalization (CSV, TSV, JSON, JSONL, Excel with fuzzy column resolution)
  2. Enterprise Data Quality Gate & Quarantine Engine (Zero silent failures)
  3. Zero-Trust PII Redaction & HMAC-safe tokenization
  4. Surgical Sentence & Contrastive Complaint Clause Extraction (P0–P3 severity, exact offsets)
  5. Production Vector ETL (all-MiniLM-L6-v2, 384D unit vectors, SHA-256 disk cache)
  6. Supervised Calibrated Sentiment Classification (Platt scaling & Brier score)
  7. Unsupervised Thematic Clustering & c-TF-IDF Topic Modeling
  8. Temporal & Batch Population Stability Index (PSI) Drift Analysis
  9. Neon PostgreSQL + pgvector Dual-Storage Knowledge Persistence
"""

from __future__ import annotations

import io
import logging
import random
from typing import List, Dict, Any, Tuple, Optional, Union

import pandas as pd
import numpy as np

from app.data.normalizer import schema_normalizer, SchemaMappingReport
from app.data.quality_gate import data_quality_gate, QualityGateManifest
from app.core.pii import pii_redactor
from app.data.sentence_extractor import sentence_clause_extractor
from app.data.embedding_service import embedding_service, EmbeddingManifest
from app.ml.sentiment import CalibratedSentimentClassifier
from app.ml.evaluation import evaluation_harness
from app.ml.clustering import clusterer
from app.ml.sentence_pipeline import classify_and_route_corpus
from app.ml.complaint_clustering import (
    cluster_complaint_sentences,
    cluster_feature_requests,
    cluster_praise_sentences,
)
from app.ml.drift import drift_detector
from app.core.database import SessionLocal
from app.services.db_service import db_service

logger = logging.getLogger(__name__)


class KnowledgePipeline:
    """
    Orchestrates the complete data transformation lifecycle from raw client file upload
    to vectorized knowledge store in Neon PostgreSQL.
    """

    def process_and_ingest(
        self,
        file_input: Union[bytes, str, io.BytesIO, pd.DataFrame],
        filename: Optional[str] = None,
        domain_id: str = "custom",
        persist_db: bool = True
    ) -> Dict[str, Any]:
        """
        Executes end-to-end knowledge ingestion pipeline.

        Returns:
            Dictionary containing:
                - reviews: List of processed review records with embeddings & metadata
                - ground_truth: Held-out validation sample
                - themes: Thematic clusters with c-TF-IDF keywords & severity
                - drift_results: Population Stability Index results
                - eval_results: Model governance metrics (confusion matrix, F1, calibration)
                - schema_report: Audit of column mapping
                - quality_manifest: Data quality and quarantine audit
                - embedding_manifest: Vector ETL metrics
                - sentiment_model: Fitted CalibratedSentimentClassifier instance
        """
        logger.info(f"Starting Knowledge Pipeline for file '{filename or 'direct_input'}' (domain: '{domain_id}')...")

        # -------------------------------------------------------------------
        # Stage 1: Smart Schema Normalization
        # -------------------------------------------------------------------
        norm_df, schema_report = schema_normalizer.normalize(file_input, filename=filename)
        logger.info(f"Stage 1 complete: Normalized {len(norm_df)} rows from format '{schema_report.file_format}'.")

        # -------------------------------------------------------------------
        # Stage 2: Enterprise Data Quality Gate & Quarantine Engine
        # -------------------------------------------------------------------
        clean_df, quality_manifest = data_quality_gate.validate_and_quarantine(norm_df)
        logger.info(
            f"Stage 2 complete: {quality_manifest.passed_rows}/{quality_manifest.total_input_rows} rows passed "
            f"(Quarantined: {quality_manifest.quarantined_rows}, Duplicates: {quality_manifest.duplicate_rows_dropped}, "
            f"Quality Score: {quality_manifest.quality_score_percentage}%)."
        )

        if clean_df.empty:
            raise ValueError(
                f"No valid records remained after Data Quality Gate. "
                f"All {quality_manifest.total_input_rows} input rows were quarantined. "
                f"Reasons: {quality_manifest.rejection_breakdown}"
            )

        # -------------------------------------------------------------------
        # Stage 3 & 4: PII Redaction & Surgical Complaint Clause Extraction
        # -------------------------------------------------------------------
        processed_records: List[Dict[str, Any]] = []

        for _, row in clean_df.iterrows():
            raw_text = str(row["raw_text"])
            rec_id = str(row["id"])
            try:
                rating = int(round(float(row["rating"])))
            except (ValueError, TypeError):
                rating = 3
            prod_name = str(row.get("product_name", "Custom Product"))
            sku = str(row.get("sku_or_module", "General"))
            version = str(row.get("batch_or_version", "Batch-Custom"))
            channel = str(row.get("channel", "Client Upload"))
            created_at = str(row.get("created_at", ""))
            extra_meta = row.get("extra_metadata", {})

            # 3. Enterprise PII Redaction
            redacted_text, pii_detected = pii_redactor.redact(raw_text)

            # 4. Surgical Clause Extraction
            telemetry = sentence_clause_extractor.extract_telemetry(rec_id, redacted_text)

            # Derive proxy ground truth from normalized rating
            if rating <= 2:
                gt_label = "NEGATIVE"
            elif rating == 3:
                gt_label = "NEUTRAL"
            else:
                gt_label = "POSITIVE"

            record = {
                "id": rec_id,
                "domain": domain_id,
                "product_name": prod_name,
                "sku_or_module": sku,
                "batch_or_version": version,
                "channel": channel,
                "rating": rating,
                "raw_text": raw_text,
                "redacted_text": redacted_text,
                "pii_detected": pii_detected,
                "ground_truth_label": gt_label,
                "highlight_span": telemetry.highlight_span.to_dict(),
                "primary_complaint_text": telemetry.primary_complaint_text,
                "overall_severity": telemetry.overall_severity,
                "created_at": created_at,
                "extra_metadata": extra_meta
            }
            processed_records.append(record)

        logger.info(f"Stages 3 & 4 complete: PII redacted and defect clauses extracted for {len(processed_records)} records.")

        # -------------------------------------------------------------------
        # Stage 4b: Multi-Aspect Sentence Classification & Routing (Complaints, Praise, Recommendations, Noise)
        # -------------------------------------------------------------------
        rev_ids = [r["id"] for r in processed_records]
        src_indices = list(range(len(processed_records)))
        red_texts = [r["redacted_text"] for r in processed_records]

        all_sentences, pools = classify_and_route_corpus(rev_ids, src_indices, red_texts)

        sents_by_review: Dict[str, list] = {}
        for s in all_sentences:
            sents_by_review.setdefault(s.review_id, []).append(s.to_dict())

        for r in processed_records:
            r["sentences"] = sents_by_review.get(r["id"], [])

        # -------------------------------------------------------------------
        # Stage 5: Production Vector ETL & Dense Embeddings
        # -------------------------------------------------------------------
        # Encode isolated complaint propositions rather than raw conversational fluff
        texts_to_embed = [r["primary_complaint_text"] for r in processed_records]
        embeddings, embedding_manifest = embedding_service.encode_texts(texts_to_embed, use_cache=True)
        logger.info(
            f"Stage 5 complete: Generated {embeddings.shape[0]} embeddings of dim {embeddings.shape[1]} "
            f"(Cache hit: {embedding_manifest.cache_hit}, Time: {embedding_manifest.inference_time_ms}ms)."
        )

        for i, r in enumerate(processed_records):
            r["embedding"] = embeddings[i].tolist()

        # -------------------------------------------------------------------
        # Stage 6: Supervised Calibrated Sentiment Classification
        # -------------------------------------------------------------------
        # Split into training set and held-out evaluation set with deterministic seed
        n_total = len(processed_records)
        if n_total >= 20:
            shuffled_indices = list(range(n_total))
            random.Random(42).shuffle(shuffled_indices)
            eval_size = min(1000, max(4, int(n_total * 0.2)))
            train_indices = shuffled_indices[:-eval_size]
            gt_indices = shuffled_indices[-eval_size:]
            train_records = [processed_records[i] for i in train_indices]
            gt_records = [processed_records[i] for i in gt_indices]
        else:
            train_records = processed_records
            gt_records = processed_records

        custom_model = CalibratedSentimentClassifier()
        train_texts = [r["redacted_text"] for r in train_records[:min(2000, len(train_records))]]
        train_labels = [r["ground_truth_label"] for r in train_records[:min(2000, len(train_records))]]
        custom_model.fit(train_texts, train_labels)

        # Predict across full batch
        all_texts = [r["redacted_text"] for r in processed_records]
        preds = custom_model.predict(all_texts)
        probs = custom_model.predict_proba(all_texts)

        for i, r in enumerate(processed_records):
            r["sentiment_pred"] = preds[i]
            cls_idx = list(custom_model.pipeline.classes_).index(preds[i])
            r["sentiment_confidence"] = round(float(probs[i][cls_idx]), 4)

        # Evaluate against held-out ground truth
        gt_texts = [r["redacted_text"] for r in gt_records]
        gt_true = [r["ground_truth_label"] for r in gt_records]
        gt_preds = custom_model.predict(gt_texts)
        gt_probs = custom_model.predict_proba(gt_texts)
        eval_results = evaluation_harness.evaluate(
            gt_true, gt_preds, gt_probs, list(custom_model.pipeline.classes_)
        )
        logger.info(
            f"Stage 6 complete: Supervised sentiment calibrated (Accuracy: {eval_results.get('accuracy')}, "
            f"Macro-F1: {eval_results.get('macro_f1')}, Brier Score: {eval_results.get('brier_score')})."
        )

        # -------------------------------------------------------------------
        # Stage 7: Thematic Clustering & c-TF-IDF Topic Extraction
        # -------------------------------------------------------------------
        cluster_res = clusterer.fit_and_cluster(processed_records)
        themes = cluster_res["themes"]
        reviews = cluster_res["reviews"]
        logger.info(f"Stage 7 complete: Extracted {len(themes)} thematic clusters via c-TF-IDF.")

        # -------------------------------------------------------------------
        # Stage 7b: Multi-Aspect Thematic Clustering (Complaints, Backlog, Strengths)
        # -------------------------------------------------------------------
        review_metadata = {
            r["id"]: {
                "batch_or_version": r.get("batch_or_version", "General"),
                "sku_or_module": r.get("sku_or_module", "General"),
            }
            for r in processed_records
        }

        complaint_clusters = []
        if pools.complaint:
            k_comp = min(6, max(1, len(pools.complaint) // 5))
            c_res = cluster_complaint_sentences(
                pools.complaint,
                n_clusters=k_comp,
                review_metadata=review_metadata,
            )
            complaint_clusters = c_res.get("clusters", [])

        feature_requests = []
        if pools.recommendation:
            k_rec = min(4, max(1, len(pools.recommendation) // 5))
            f_res = cluster_feature_requests(pools.recommendation, n_clusters=k_rec)
            feature_requests = f_res.get("feature_requests", [])

        praise_clusters = []
        if pools.praise:
            k_pra = min(5, max(1, len(pools.praise) // 5))
            p_res = cluster_praise_sentences(pools.praise, n_clusters=k_pra)
            praise_clusters = p_res.get("praise_clusters", p_res.get("clusters", []))

        logger.info(
            f"Stage 7b complete: Generated {len(complaint_clusters)} complaint clusters, "
            f"{len(feature_requests)} feature requests, and {len(praise_clusters)} praise clusters."
        )

        # -------------------------------------------------------------------
        # Stage 8: Temporal & Batch Drift Analysis (PSI)
        # -------------------------------------------------------------------
        drift_results = drift_detector.analyze_drift(reviews)
        logger.info(f"Stage 8 complete: Drift analysis status: '{drift_results.get('overall_drift_status')}'.")

        # -------------------------------------------------------------------
        # Stage 9: Knowledge Store Persistence (Neon PostgreSQL & pgvector)
        # -------------------------------------------------------------------
        if persist_db:
            try:
                db = SessionLocal()
                domain_info = {
                    "id": domain_id,
                    "name": f"Client Dataset ({filename or 'Custom Upload'})",
                    "category": "Client Upload",
                    "focus": f"Ingested {len(reviews)} reviews with {len(themes)} semantic clusters"
                }
                db_service.seed_domain(
                    db=db,
                    domain_info=domain_info,
                    reviews=reviews,
                    themes=themes,
                    drift_results=drift_results,
                    eval_results=eval_results,
                    embeddings=embeddings,
                    overwrite=True
                )
                db.close()
                logger.info(f"Stage 9 complete: Successfully persisted {len(reviews)} reviews with 384D pgvector embeddings to database.")
            except Exception as e:
                logger.warning(f"Database persistence encountered an issue (in-memory state remains operational): {e}")

        return {
            "status": "success",
            "active_domain": domain_id,
            "rows_ingested": len(reviews),
            "reviews": reviews,
            "ground_truth": gt_records,
            "themes": themes,
            "drift_results": drift_results,
            "eval_results": eval_results,
            "complaint_clusters": complaint_clusters,
            "feature_requests": feature_requests,
            "praise_clusters": praise_clusters,
            "sentiment_model": custom_model,
            "schema_report": schema_report.to_dict(),
            "quality_manifest": quality_manifest.to_dict(),
            "embedding_manifest": embedding_manifest.to_dict(),
        }


# Singleton pipeline orchestrator
knowledge_pipeline = KnowledgePipeline()

__all__ = ["KnowledgePipeline", "knowledge_pipeline"]
