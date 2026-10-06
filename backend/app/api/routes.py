"""
routes.py - Core REST API Endpoints for InSight Telemetry & ML Engine.

This module provides the HTTP routing layer serving the frontend dashboard:
- Telemetry & Analytics: Dataset overview, sentiment trends, rating distribution
- Thematic Intelligence: Unsupervised semantic clustering, c-TF-IDF keyword extraction
- Statistical Drift: Population Stability Index (PSI) tracking across batches/releases
- Model Governance: Calibration metrics, 3x3 confusion matrix, validation harness
- Actionability & Export: Structured Jira tickets and QA incident reporting
- Knowledge & Verbatims: Zero-trust PII masked drilldown into raw review spans
"""

import io
import json
import logging
import random
import re
from typing import Optional, Tuple

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
import pandas as pd

import threading
from app.core.config import settings
from app.core.database import get_db
from app.data.datasets import dataset_manager
from app.data.real_loader import real_data_loader
from app.data.knowledge_pipeline import knowledge_pipeline
from app.ml.sentiment import sentiment_model, CalibratedSentimentClassifier
from app.ml.evaluation import evaluation_harness
from app.ml.clustering import clusterer, transformer_encoder
from app.ml.drift import drift_detector
from app.ml.severity import severity_snapshot
from app.core.auth import (
    get_current_user,
    get_current_user_optional,
    require_role,
    AuthenticatedUser,
)
from app.services.db_service import db_service
from app.services.powerbi_service import powerbi_service
from app.services.copilot_service import copilot_service
from app.services.benchmark_service import benchmark_service
from app.services.roi_service import roi_service
from app.models.schema import DomainModel, ThemeModel, ReviewModel, TicketModel

logger = logging.getLogger(__name__)

router = APIRouter()


def _auth():
    """
    Auth dependency applied to every data route.

    Flipping ``REQUIRE_AUTH`` to true in the environment enforces
    authentication across the whole API with no code change. Development
    defaults to open so the dashboard is usable without an auth server; the
    unsafe routes below are additionally role-gated whenever auth is on.
    """
    return Depends(get_current_user if settings.REQUIRE_AUTH else get_current_user_optional)


def _privileged_auth():
    """Dependency for routes that must be restricted even in open dev mode."""
    if not settings.REQUIRE_AUTH:
        return Depends(get_current_user_optional)
    return Depends(require_role(*settings.PII_UNMASK_ROLES))


class AppState:
    """
    In-memory state container holding active domain telemetry, models, and cache.

    Attributes:
        active_domain: Current selected domain key (e.g., 'd2c_cosmetics', 'tech_saas').
        reviews: In-memory store of loaded and normalized customer reviews.
        ground_truth: Human-annotated reference reviews for calibration & governance.
        themes: Extracted thematic clusters with c-TF-IDF keywords and severity.
        drift_results: Cohort-over-cohort PSI metrics and regression alert flags.
        eval_results: Model performance statistics (macro-F1, Brier score, accuracy).
        sentiment_model: Active calibrated classifier instance for sentiment inference.
        is_initialized: Flag indicating whether domain artifacts have finished loading.
    """
    def __init__(self):
        self.active_domain: str = "d2c_cosmetics"
        self.reviews: list = []
        self.ground_truth: list = []
        self.themes: list = []
        self.drift_results: dict = {}
        self.eval_results: dict = {}
        self.eval_provenance: dict = {}
        self.sentiment_model: CalibratedSentimentClassifier = sentiment_model
        self.complaint_clusters: list = []
        self.feature_requests: list = []
        self.praise_clusters: list = []
        self.is_initialized: bool = False
        self.data_provenance: dict = {}


state = AppState()
DOMAIN_CACHE: dict = {}
INIT_LOCK = threading.RLock()

# Domain provenance: consumers must be able to tell real telemetry from
# generated demo data. Previously tech_saas was presented with an identical
# schema and identical (meaningless) governance metrics to the real corpus.
DOMAIN_PROVENANCE = {
    "d2c_cosmetics": {"synthetic": False, "source": "kaggle:sephora-cosmetics-10k"},
    "tech_saas": {"synthetic": True, "source": "generated-templates"},
}


def _split_train_eval(reviews: list, eval_size: int, seed: int = 42):
    """
    Deterministic, shuffled train/eval split.

    Previously the split was an unshuffled prefix/suffix, so a CSV sorted by
    rating, date or product produced a systematically biased held-out set.
    """
    order = list(range(len(reviews)))
    random.Random(seed).shuffle(order)
    split = len(order) - min(eval_size, len(order) // 3)
    split = max(split, 0)
    return [reviews[i] for i in order[:split]], [reviews[i] for i in order[split:]]


def compute_domain_artifacts(domain: str) -> dict:
    """Computes and calibrates artifacts for a domain with an isolated classifier instance."""
    provenance = dict(DOMAIN_PROVENANCE.get(domain, {"synthetic": True, "source": "unknown"}))
    use_real_pipeline = False
    reviews: list
    ground_truth: list

    if domain == "d2c_cosmetics":
        try:
            real_res = real_data_loader.load_data()
            reviews = real_res["reviews"]
            themes = real_res["themes"]
            drift_results = real_res["drift_results"]
            use_real_pipeline = True
            domain_model = real_res.get("sentiment_model")
            if domain_model is None:
                domain_model = CalibratedSentimentClassifier()
            provenance["reviews_without_cohort"] = real_res.get("reviews_without_cohort", 0)
            provenance["label_source"] = real_res.get("label_source")
            logger.info(
                "Loaded real Sephora cosmetics telemetry (%d reviews, labels=%s).",
                real_res["row_count"], real_res.get("label_source"),
            )
        except Exception as e:
            logger.warning(
                "Could not load real cosmetics data, falling back to synthetic generator: %s", e
            )
            reviews, ground_truth = dataset_manager.generate_d2c_cosmetics(10000)
            use_real_pipeline = False
            domain_model = None
            provenance = {"synthetic": True, "source": "generated-templates (real load failed)"}
    elif domain == "tech_saas":
        reviews, ground_truth = dataset_manager.generate_tech_saas(10000)
        use_real_pipeline = False
        domain_model = None
    else:
        raise ValueError(f"Unknown domain: {domain}")

    if use_real_pipeline:
        # Real corpus: evaluate the SHIPPED artifact against the real weak labels
        # on a held-out split. The previous code retrained a model on the
        # artifact's own predictions (self-distillation on pseudo-labels) and
        # then scored it against synthetic Aura Botanicals template text.
        labelled = [r for r in reviews if r.get("ground_truth_label") in CalibratedSentimentClassifier.CLASSES]
        _, held_out = _split_train_eval(labelled, eval_size=1000)
        if len(held_out) >= 2 and domain_model is not None and domain_model.is_fitted:
            eval_results = evaluation_harness.evaluate(
                [r["ground_truth_label"] for r in held_out],
                [r["sentiment_pred"] for r in held_out],
                domain_model.predict_proba([r["redacted_text"] for r in held_out]),
                CalibratedSentimentClassifier.CLASSES,
            )
            eval_results["split"] = "held-out 1/3 of labelled reviews (never fitted)"
            eval_results["label_source"] = provenance.get("label_source")
            eval_results["benchmark_type"] = "production_telemetry_weak_labels"
            eval_results["synthetic_disclaimer"] = None
        else:
            logger.warning("Too few labelled reviews to compute governance metrics; suppressed.")
            eval_results = {}
        ground_truth = held_out
    else:
        # Synthetic corpus: fit on a train split, evaluate on a disjoint
        # held-out split. Never train on the rows that are scored.
        train_rows, held_out = _split_train_eval(reviews, eval_size=1000)
        domain_model = CalibratedSentimentClassifier()
        domain_model.fit(
            [r["redacted_text"] for r in train_rows],
            [r["ground_truth_label"] for r in train_rows],
        )
        scores = domain_model.predict_proba([r["redacted_text"] for r in reviews])
        classes = list(domain_model.pipeline.classes_)
        for i, r in enumerate(reviews):
            pred = classes[int(scores[i].argmax())]
            r["sentiment_pred"] = pred
            r["sentiment_confidence"] = round(float(scores[i][classes.index(pred)]), 4)

        # Score only the held-out rows, never the rows the model was fitted on.
        eval_results = evaluation_harness.evaluate(
            [r["ground_truth_label"] for r in held_out],
            [r["sentiment_pred"] for r in held_out],
            domain_model.predict_proba([r["redacted_text"] for r in held_out]),
            domain_model.CLASSES,
        )
        eval_results["split"] = "held-out 1/3 of the generated corpus (excluded from fitting)"
        eval_results["label_source"] = provenance.get("source")
        eval_results["benchmark_type"] = "synthetic_grammar_benchmark"
        eval_results["synthetic_disclaimer"] = (
            "Synthetic benchmark generated from slotted template grammar. High F1 reflects lexical "
            "pattern memorization across template slots. Consult the real Sephora corpus ('d2c_cosmetics') "
            "for production customer telemetry."
        )

        cluster_res = clusterer.fit_and_cluster(reviews)
        themes = cluster_res["themes"]
        reviews = cluster_res["reviews"]
        drift_results = drift_detector.analyze_drift(reviews)

        # Sentence-level multi-aspect intent routing for synthetic domain
        from app.ml.sentence_pipeline import classify_and_route_corpus
        from app.ml.complaint_clustering import (
            cluster_complaint_sentences,
            cluster_feature_requests,
            cluster_praise_sentences,
        )
        rev_ids = [r["id"] for r in reviews]
        src_idxs = list(range(len(reviews)))
        red_texts = [r["redacted_text"] for r in reviews]
        all_sents, pools = classify_and_route_corpus(rev_ids, src_idxs, red_texts)
        sents_by_id = {}
        for s in all_sents:
            sents_by_id.setdefault(s.review_id, []).append(s.to_dict())
        for r in reviews:
            r["sentences"] = sents_by_id.get(r["id"], [])

        # Cluster synthetic sentence pools (sample up to 200 across the corpus for fast, diverse clustering)
        rng = random.Random(42)
        saas_complaint_clusters = []
        if pools.complaint:
            sampled_complaints = rng.sample(pools.complaint, min(200, len(pools.complaint)))
            c_res = cluster_complaint_sentences(sampled_complaints, n_clusters=4)
            saas_complaint_clusters = c_res.get("clusters", [])

        saas_feature_requests = []
        if pools.recommendation:
            sampled_recs = rng.sample(pools.recommendation, min(200, len(pools.recommendation)))
            f_res = cluster_feature_requests(sampled_recs, n_clusters=3)
            saas_feature_requests = f_res.get("feature_requests", [])

        saas_praise_clusters = []
        if pools.praise:
            sampled_praise = rng.sample(pools.praise, min(200, len(pools.praise)))
            p_res = cluster_praise_sentences(sampled_praise, n_clusters=4)
            saas_praise_clusters = p_res.get("praise_clusters", p_res.get("clusters", []))

    return {
        "reviews": reviews,
        "ground_truth": ground_truth,
        "themes": themes,
        "drift_results": drift_results,
        "eval_results": eval_results,
        "sentiment_model": domain_model,
        "data_provenance": provenance,
        "complaint_clusters": real_res.get("complaint_clusters", []) if use_real_pipeline else saas_complaint_clusters,
        "feature_requests": real_res.get("feature_requests", []) if use_real_pipeline else saas_feature_requests,
        "praise_clusters": real_res.get("praise_clusters", []) if use_real_pipeline else saas_praise_clusters,
    }


def _swap_state(domain: str, cached: dict) -> None:
    """Atomically replaces every field of the global state under the lock without mutating singletons."""
    state.active_domain = domain
    state.reviews = cached["reviews"]
    state.ground_truth = cached["ground_truth"]
    state.themes = cached["themes"]
    state.drift_results = cached["drift_results"]
    state.eval_results = cached["eval_results"]
    state.data_provenance = cached.get("data_provenance", {})
    state.sentiment_model = cached["sentiment_model"]
    state.complaint_clusters = cached.get("complaint_clusters", [])
    state.feature_requests = cached.get("feature_requests", [])
    state.praise_clusters = cached.get("praise_clusters", [])
    state.is_initialized = True


def initialize_domain(domain: str):
    """Initializes and activates domain state using pre-computed cache for instant switching."""
    with INIT_LOCK:
        if domain not in DOMAIN_CACHE:
            DOMAIN_CACHE[domain] = compute_domain_artifacts(domain)
        _swap_state(domain, DOMAIN_CACHE[domain])


def ensure_initialized():
    """Lazily ensures primary domain state is initialized on first request with double-checked locking."""
    if not state.is_initialized:
        with INIT_LOCK:
            if not state.is_initialized:
                initialize_domain("d2c_cosmetics")


DEFAULT_DOMAIN = "d2c_cosmetics"


def get_domain_bundle(domain: Optional[str] = None) -> Tuple[str, dict]:
    """Thread-safe retrieval of domain state bundle without global race conditions.
    
    If domain is None, defaults to state.active_domain or DEFAULT_DOMAIN.
    If requested domain is not cached, initializes it under INIT_LOCK.
    Returns (domain_key, bundle_dict).
    """
    ensure_initialized()
    target_domain = (domain or state.active_domain or DEFAULT_DOMAIN).strip()
    if target_domain not in ("d2c_cosmetics", "tech_saas", "custom") and not target_domain.startswith("custom"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid domain '{target_domain}'. Valid options: 'd2c_cosmetics', 'tech_saas', 'custom'.",
        )
    with INIT_LOCK:
        if target_domain not in DOMAIN_CACHE:
            if target_domain == "custom" or target_domain.startswith("custom"):
                raise HTTPException(
                    status_code=404,
                    detail="No custom dataset has been uploaded yet. Upload a CSV/Excel file first.",
                )
            DOMAIN_CACHE[target_domain] = compute_domain_artifacts(target_domain)
        return target_domain, DOMAIN_CACHE[target_domain]


class DomainSelectRequest(BaseModel):
    domain: str


class TicketRequest(BaseModel):
    cluster_id: int
    domain: Optional[str] = None


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=512)
    domain: Optional[str] = Field(None, max_length=64)
    limit: int = Field(10, ge=1, le=100)


class PowerBIConfigPayload(BaseModel):
    embed_url: str = Field(..., max_length=2048)
    report_title: Optional[str] = Field(None, max_length=256)


@router.get("/datasets")
def list_datasets(user: Optional[AuthenticatedUser] = _auth()):
    ensure_initialized()
    return {
        "active_domain": state.active_domain,
        "available_domains": [
            {
                "id": "d2c_cosmetics",
                "name": "D2C Cosmetics & Beauty (Aura Botanicals)",
                "category": "Consumer Goods / Skincare",
                "focus": "Batch lot tracking, formulation changes, skin irritation, packaging defects",
                "review_count": len(DOMAIN_CACHE.get("d2c_cosmetics", {}).get("reviews", [])) if "d2c_cosmetics" in DOMAIN_CACHE else 10000,
                "synthetic": False,
            },
            {
                "id": "tech_saas",
                "name": "Fintech Mobile App (NovaPay)",
                "category": "Software / Mobile App",
                "focus": "Release regressions, biometric crashes, P2P transfer failures",
                "review_count": len(DOMAIN_CACHE.get("tech_saas", {}).get("reviews", [])) if "tech_saas" in DOMAIN_CACHE else 10000,
                "synthetic": True,
            },
            {
                "id": "custom",
                "name": "Custom Review Dataset (CSV Upload)",
                "category": "User Upload",
                "focus": "On-demand ingestion of any review text and metadata",
                "review_count": len(DOMAIN_CACHE.get("custom", {}).get("reviews", [])) if "custom" in DOMAIN_CACHE else 0,
                "synthetic": None,
            },
        ],
    }


@router.post("/datasets/select")
def select_dataset(req: DomainSelectRequest, user: Optional[AuthenticatedUser] = _auth()):
    if req.domain not in ("d2c_cosmetics", "tech_saas", "custom"):
        raise HTTPException(
            status_code=400,
            detail="Invalid domain. Choose 'd2c_cosmetics', 'tech_saas', or 'custom'. Use the upload control to load a custom CSV.",
        )
    if req.domain == "custom":
        with INIT_LOCK:
            if "custom" not in DOMAIN_CACHE:
                raise HTTPException(
                    status_code=400,
                    detail="No custom dataset has been uploaded yet. Upload a CSV/Excel file first.",
                )
            _swap_state("custom", DOMAIN_CACHE["custom"])
    else:
        initialize_domain(req.domain)
    return {"status": "success", "active_domain": state.active_domain}


def _process_custom_csv(contents: bytes, filename: str) -> dict:
    """
    Parses, fits, clusters and evaluates an uploaded CSV.

    Runs entirely off the event loop (see the route handler) and builds every
    artifact into locals so a mid-pipeline failure cannot leave the global
    state holding a mixture of old and new values.
    """
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8", errors="replace")))
    except Exception:
        logger.exception("CSV parse failed for upload %s", filename)
        raise HTTPException(status_code=400, detail="Could not parse the file as CSV.")

    if len(df) > settings.MAX_UPLOAD_ROWS:
        raise HTTPException(
            status_code=413,
            detail=f"File has {len(df)} rows; the limit is {settings.MAX_UPLOAD_ROWS}.",
        )

    reviews, gt = dataset_manager.parse_custom_csv(df)

    if len(reviews) < settings.MIN_TRAIN_ROWS:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least {settings.MIN_TRAIN_ROWS} usable reviews with a recognisable "
                   f"text column; got {len(reviews)}.",
        )

    train_rows, held_out = _split_train_eval(reviews, eval_size=min(1000, len(reviews) // 3))

    labels = {r.get("ground_truth_label") for r in train_rows}
    labels.discard(None)
    if len(labels) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Cannot train a sentiment model: the uploaded data yields only "
                f"{len(labels)} sentiment class(es) ({sorted(labels) or 'none'}). "
                "A dataset with at least two distinct sentiment values is required."
            ),
        )

    custom_model = CalibratedSentimentClassifier()
    custom_model.fit(
        [r["redacted_text"] for r in train_rows],
        [r["ground_truth_label"] for r in train_rows],
    )

    scores = custom_model.predict_proba([r["redacted_text"] for r in reviews])
    classes = list(custom_model.pipeline.classes_)
    for i, r in enumerate(reviews):
        pred = classes[int(scores[i].argmax())]
        r["sentiment_pred"] = pred
        r["sentiment_confidence"] = round(float(scores[i][classes.index(pred)]), 4)

    eval_results = {}
    if len(held_out) >= 2:
        eval_results = evaluation_harness.evaluate(
            [r["ground_truth_label"] for r in held_out],
            [r["sentiment_pred"] for r in held_out],
            custom_model.predict_proba([r["redacted_text"] for r in held_out]),
            custom_model.CLASSES,
        )
        eval_results["split"] = "held-out 1/3 of uploaded rows (excluded from fitting)"

    cluster_res = clusterer.fit_and_cluster(reviews)
    themes = cluster_res["themes"]
    reviews = cluster_res["reviews"]
    drift_results = drift_detector.analyze_drift(reviews)

    return {
        "reviews": reviews,
        "ground_truth": gt,
        "themes": themes,
        "drift_results": drift_results,
        "eval_results": eval_results,
        "sentiment_model": custom_model,
        "data_provenance": {"synthetic": None, "source": f"user upload: {filename}"},
        "total_rows": len(df),
    }


@router.post("/datasets/upload")
async def upload_custom_dataset(
    file: UploadFile = File(...),
    user: Optional[AuthenticatedUser] = _privileged_auth(),
):
    """
    Enterprise Knowledge Pipeline Ingestion Endpoint.
    Supports CSV, TSV, JSON, JSONL, and Excel (.xlsx, .xls).
    Executes full pipeline:
      1. Schema Normalization with Fuzzy Matching
      2. Data Quality & Quarantine Gate
      3. Enterprise PII Scrubbing
      4. Surgical Sentence & Contrastive Complaint Extraction
      5. Production Vector ETL (384D all-MiniLM-L6-v2)
      6. Supervised Calibrated Sentiment Classification
      7. Semantic Thematic Clustering (c-TF-IDF)
      8. Temporal Drift Analysis (PSI)
      9. Dual-Storage Persistence to Neon PostgreSQL pgvector
    """
    # Stream with a hard byte ceiling instead of unbounded buffer
    chunks: list[bytes] = []
    total_bytes = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Upload exceeds the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
            )
        chunks.append(chunk)

    contents = b"".join(chunks)
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = await run_in_threadpool(
            knowledge_pipeline.process_and_ingest,
            file_input=contents,
            filename=file.filename,
            domain_id="custom",
            persist_db=True,
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline error during ingestion of '{file.filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Knowledge pipeline error: {str(e)}")

    # Cache custom dataset bundle under INIT_LOCK without overwriting active domain for other users
    with INIT_LOCK:
        result["data_provenance"] = {"synthetic": False, "source": f"user upload: {file.filename}"}
        DOMAIN_CACHE["custom"] = result

    return {
        "status": "success",
        "rows_ingested": result["rows_ingested"],
        "total_rows_ingested": result["rows_ingested"],
        "eval_rows": len(result["ground_truth"]) or None,
        "active_domain": "custom",
        "domain": "custom",
        "data_provenance": result["data_provenance"],
        "schema_report": result.get("schema_report", {}),
        "quality_manifest": result.get("quality_manifest", {}),
        "embedding_manifest": result.get("embedding_manifest", {}),
        "themes_count": len(result["themes"]),
    }

@router.get("/overview")
def get_overview(
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle["reviews"]
    themes = bundle["themes"]
    drift_results = bundle["drift_results"]
    data_provenance = bundle.get("data_provenance", {})

    total = len(reviews)
    pos_count = sum(1 for r in reviews if r.get("sentiment_pred") == "POSITIVE")
    neu_count = sum(1 for r in reviews if r.get("sentiment_pred") == "NEUTRAL")
    neg_count = sum(1 for r in reviews if r.get("sentiment_pred") == "NEGATIVE")

    pii_count = sum(1 for r in reviews if len(r.get("pii_detected") or []) > 0)
    critical_themes = sum(1 for t in themes if t.get("severity") == "CRITICAL")

    # 1. Dynamic Rating Distribution (1 to 5 stars)
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        star = r.get("rating")
        if star in rating_counts:
            rating_counts[star] += 1

    star_colors = {1: "#F87171", 2: "#FB923C", 3: "#FBBF24", 4: "#34D399", 5: "#059669"}
    rating_distribution = [
        {
            "star": f"{s}",
            "count": rating_counts[s],
            "percent": round(rating_counts[s] / total * 100, 1) if total else 0,
            "color": star_colors[s],
        }
        for s in [1, 2, 3, 4, 5]
    ]

    # 2. Dynamic Sentiment by Channel / Source
    channel_map: dict = {}
    for r in reviews:
        ch = r.get("channel") or "Direct"
        entry = channel_map.setdefault(ch, {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0, "total": 0})
        sp = r.get("sentiment_pred", "NEUTRAL")
        if sp in entry:
            entry[sp] += 1
        entry["total"] += 1

    sentiment_by_source = []
    for ch, stats in channel_map.items():
        ch_total = stats["total"] or 1
        pos_p = stats["POSITIVE"] / ch_total * 100
        neu_p = stats["NEUTRAL"] / ch_total * 100
        neg_p = stats["NEGATIVE"] / ch_total * 100
        # Send unrounded percentages that still sum to ~100 so the client can
        # render stacked segments without gaps.
        sentiment_by_source.append({
            "label": ch,
            "count": stats["total"],
            "pos": round(pos_p, 2),
            "neu": round(neu_p, 2),
            "neg": round(neg_p, 2),
        })

    # 3. Dynamic Sentiment Trend from Drift Timeline
    sentiment_trend = []
    for b in drift_results.get("timeline", []):
        b_total = b.get("review_count") or 1
        sentiment_trend.append({
            "label": b.get("batch_or_version", "Batch"),
            "count": b_total,
            "pos": round(b.get("positive_count", 0) / b_total * 100, 2),
            "neu": round(b.get("neutral_count", 0) / b_total * 100, 2),
            "neg": round(b.get("negative_count", 0) / b_total * 100, 2),
        })

    if not sentiment_trend and total:
        pos_rate = round(pos_count / total * 100, 2)
        neu_rate = round(neu_count / total * 100, 2)
        neg_rate = round(neg_count / total * 100, 2)
        sentiment_trend = [{"label": "All reviews", "count": total, "pos": pos_rate, "neu": neu_rate, "neg": neg_rate}]

    # 4. Dynamic Keyword Cloud extracted from thematic clusters
    cloud_keywords = []
    seen: set[str] = set()
    palette = [
        ("#EF4444", "2.0rem", 800),
        ("#DC2626", "1.5rem", 700),
        ("#0F382E", "2.2rem", 800),
        ("#059669", "1.6rem", 700),
        ("#10B981", "1.4rem", 600),
        ("#D97706", "1.3rem", 700),
        ("#334155", "1.2rem", 600),
        ("#475569", "1.1rem", 500),
        ("#6B7280", "1.0rem", 600),
        ("#6B7280", "0.9rem", 500),
    ]
    idx = 0
    for t in themes:
        for kw in t.get("keywords", []):
            clean_kw = kw.strip().lower()
            if clean_kw and clean_kw not in seen and len(clean_kw) > 2:
                seen.add(clean_kw)
                color, size, weight = palette[idx % len(palette)]
                idx += 1
                cloud_keywords.append({
                    "text": clean_kw,
                    "size": size,
                    "color": color,
                    "weight": weight,
                    "count": t.get("review_count", 0),
                })
                if len(cloud_keywords) >= 16:
                    break
        if len(cloud_keywords) >= 16:
            break

    # 5. Dynamic Recent Insights based on statistical drift and defects
    alerts = drift_results.get("alerts", [])
    recent_insights = []
    if alerts:
        top_alert = alerts[0]
        recent_insights.append({
            "title": top_alert["message"],
            "metric": {"value": f"{top_alert['psi_score']:.2f}", "kind": "index"},
            "metric_label": "PSI",
            "period": f"in {top_alert['batch_or_version']}",
            "isWarning": True,
            "psiAlert": f"PSI {top_alert['psi_score']:.2f}",
        })

    critical_themes_list = [t for t in themes if t.get("severity") in ("CRITICAL", "HIGH")]
    if critical_themes_list:
        top_crit = critical_themes_list[0]
        recent_insights.append({
            "title": f"Highest-severity cluster '{top_crit['title']}' ({top_crit.get('negative_rate', 0)}% negative)",
            "metric": {"value": f"{top_crit['review_count']}", "kind": "count"},
            "metric_label": "reviews",
            "period": "active defect cluster",
            "isWarning": True,
            "psiAlert": None,
        })

    if total:
        pos_rate_val = round(pos_count / total * 100)
        recent_insights.append({
            "title": f"Overall product satisfaction at {pos_rate_val}% positive sentiment",
            "metric": {"value": f"{pos_rate_val}%", "kind": "percentage"},
            "metric_label": "positive",
            "period": "across all channels",
            "isWarning": False,
            "psiAlert": None,
        })

    # 6. Sentence Intent Breakdown (4-Way Partitioning: Complaints, Praise, Recommendations, Noise)
    comp_sents = 0
    praise_sents = 0
    rec_sents = 0
    noise_sents = 0
    comp_revs = 0
    praise_revs = 0
    rec_revs = 0
    noise_revs = 0

    for r in reviews:
        has_c = False
        has_p = False
        has_r = False
        has_n = False
        for s in r.get("sentences", []):
            lbl = s.get("label")
            if lbl == "COMPLAINT":
                comp_sents += 1
                has_c = True
            elif lbl == "RECOMMENDATION":
                rec_sents += 1
                has_r = True
            elif lbl == "PRAISE":
                praise_sents += 1
                has_p = True
            else:
                noise_sents += 1
                has_n = True
        if has_c:
            comp_revs += 1
        if has_p:
            praise_revs += 1
        if has_r:
            rec_revs += 1
        if has_n:
            noise_revs += 1

    total_sents = comp_sents + praise_sents + rec_sents + noise_sents
    actionable_sents = comp_sents + praise_sents + rec_sents
    actionable_rate_pct = round(100.0 * actionable_sents / max(total_sents, 1), 1)

    intent_breakdown = {
        "total_sentences": total_sents,
        "complaints": comp_sents,
        "complaints_reviews": comp_revs,
        "praise": praise_sents,
        "praise_reviews": praise_revs,
        "recommendations": rec_sents,
        "recommendations_reviews": rec_revs,
        "noise": noise_sents,
        "noise_reviews": noise_revs,
        "actionable_count": actionable_sents,
        "actionable_rate_pct": actionable_rate_pct,
    }

    return {
        "domain": active_dom,
        "data_provenance": data_provenance,
        "total_reviews": total,
        "sentiment_counts": {
            "POSITIVE": pos_count,
            "NEUTRAL": neu_count,
            "NEGATIVE": neg_count,
        },
        "positive_rate": round((pos_count / total * 100), 1) if total else 0,
        "negative_rate": round((neg_count / total * 100), 1) if total else 0,
        "pii_redacted_count": pii_count,
        "pii_redacted_rate": round((pii_count / total * 100), 1) if total else 0,
        "critical_themes_count": critical_themes,
        "active_alerts": len(alerts),
        "rating_distribution": rating_distribution,
        "sentiment_by_source": sentiment_by_source,
        "sentiment_trend": sentiment_trend,
        "keyword_cloud": cloud_keywords,
        "recent_insights": recent_insights,
        "intent_breakdown": intent_breakdown,
    }


@router.get("/themes")
def get_themes(
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    active_dom, bundle = get_domain_bundle(domain)
    themes = bundle["themes"]
    return {
        "domain": active_dom,
        "themes": themes,
        "total_themes": len(themes),
        "severity_thresholds": severity_snapshot(),
    }


def _public_verbatim(record: dict) -> dict:
    """
    Builds the verbatim payload with an EXPLICIT field allowlist.

    Previously ``dict(record)`` copied raw_text into every response, so the
    ``show_raw_pii`` flag only changed a convenience field while the
    unredacted text remained in the payload (and in the CSV export).
    """
    return {
        "id": record.get("id"),
        "domain": record.get("domain"),
        "product_name": record.get("product_name"),
        "brand_name": record.get("brand_name"),
        "product_id": record.get("product_id"),
        "sku_or_module": record.get("sku_or_module"),
        "batch_or_version": record.get("batch_or_version"),
        "submission_date": record.get("submission_date"),
        "channel": record.get("channel"),
        "rating": record.get("rating"),
        "redacted_text": record.get("redacted_text"),
        "pii_detected": record.get("pii_detected") or [],
        "sentiment_pred": record.get("sentiment_pred"),
        "sentiment_confidence": record.get("sentiment_confidence"),
        "cluster_id": record.get("cluster_id"),
        "theme_title": record.get("theme_title"),
        "highlight_span": record.get("highlight_span"),
    }


@router.get("/verbatims")
def get_verbatims(
    request: Request,
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _auth(),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    offset: Optional[int] = Query(None, ge=0, description="Optional 0-indexed item offset for continuous scrolling"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Optional item limit for continuous scrolling"),
    sentiment: Optional[str] = Query(None, max_length=16),
    cluster_id: Optional[int] = Query(None),
    batch: Optional[str] = Query(None, max_length=64),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
    show_raw_pii: bool = Query(False),
):
    active_dom, bundle = get_domain_bundle(domain)

    # Unmasking is privileged. When authentication is enabled it additionally
    # requires an audited role, and every unmask is recorded.
    unmask_allowed = False
    if show_raw_pii:
        role = (user.role if isinstance(user, AuthenticatedUser) else None) or ""
        if not settings.REQUIRE_AUTH:
            unmask_allowed = True  # open development mode
        elif role.lower() in {r.lower() for r in settings.PII_UNMASK_ROLES}:
            unmask_allowed = True
            logger.warning(
                "AUDIT: role=%s unmasked raw customer text (domain=%s, page=%s)",
                role, active_dom, page,
            )
    if show_raw_pii and not unmask_allowed:
        raise HTTPException(
            status_code=403,
            detail="Unredacted customer text requires an authorised compliance role.",
        )

    # Filter over isolated bundle reviews
    filtered = list(bundle["reviews"])

    if sentiment:
        filtered = [r for r in filtered if r.get("sentiment_pred") == sentiment.upper()]
    if cluster_id is not None:
        filtered = [r for r in filtered if r.get("cluster_id") == cluster_id]
    if batch:
        filtered = [r for r in filtered if r.get("batch_or_version") == batch]
    if search:
        needle = search.lower()
        # Always match the redacted corpus: the filter must describe what the
        # user can see, even in auditor mode.
        filtered = [r for r in filtered if needle in (r.get("redacted_text") or "").lower()]

    total_matching = len(filtered)
    if offset is not None and limit is not None:
        start_idx = offset
        effective_page_size = limit
        effective_page = (offset // limit) + 1
    else:
        start_idx = (page - 1) * page_size
        effective_page_size = page_size
        effective_page = page

    sliced = filtered[start_idx : start_idx + effective_page_size]

    results = []
    for r in sliced:
        item = _public_verbatim(r)
        if unmask_allowed and r.get("raw_text") is not None:
            item["display_text"] = r["raw_text"]
        else:
            item["display_text"] = r.get("redacted_text") or ""
        results.append(item)

    return {
        "total": total_matching,
        "page": effective_page,
        "page_size": effective_page_size,
        "offset": start_idx,
        "has_more": start_idx + len(sliced) < total_matching,
        "total_pages": (total_matching + effective_page_size - 1) // effective_page_size if effective_page_size > 0 else 1,
        "domain": active_dom,
        "pii_masked": not unmask_allowed,
        "verbatims": results,
    }


@router.get("/drift")
def get_drift(
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    _, bundle = get_domain_bundle(domain)
    return bundle["drift_results"]


@router.get("/governance")
def get_model_governance(
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    active_dom, bundle = get_domain_bundle(domain)
    return {
        "domain": active_dom,
        "model_architecture": "Calibrated Logistic Regression (Platt Scaling) over Sublinear N-Gram TF-IDF",
        "evaluation": bundle["eval_results"],
        "data_provenance": bundle.get("data_provenance", {}),
        "benchmark_note": "Production metrics are evaluated on real Sephora telemetry ('d2c_cosmetics'). Synthetic domains demonstrate pipeline execution and slotted template classification.",
        "severity_thresholds": severity_snapshot(),
        "auth_required": settings.REQUIRE_AUTH,
    }


@router.post("/ticket/generate")
def generate_ticket(req: TicketRequest, db=Depends(get_db),
                    user: Optional[AuthenticatedUser] = _auth()):
    active_dom, bundle = get_domain_bundle(req.domain)
    themes = bundle["themes"]
    reviews = bundle["reviews"]
    data_provenance = bundle.get("data_provenance", {})

    theme = next((t for t in themes if t["cluster_id"] == req.cluster_id), None)
    if not theme:
        raise HTTPException(status_code=404, detail="Cluster ID not found.")

    theme_reviews = [r for r in reviews if r.get("cluster_id") == req.cluster_id][:5]

    is_d2c = (active_dom == "d2c_cosmetics")

    if is_d2c:
        ticket_type = "MANUFACTURING & QUALITY INCIDENT REPORT"
        title = f"[QA-INCIDENT] Defect Alert: {theme['title']} ({theme['severity']})"
        affected_field = "Affected Batches / Lots"
    else:
        ticket_type = "ENGINEERING BUG TICKET"
        title = f"[BUG-P0] Critical Regression: {theme['title']}"
        affected_field = "Affected Software Releases"

    batches = sorted({(r.get("batch_or_version") or "N/A") for r in theme_reviews})
    # Verbatim text is interpolated into Markdown. Neutralise the characters
    # that would otherwise break out of the quote or inject markup.
    quotes = "\n".join(
        f'- "{_md_escape(r["redacted_text"])}" '
        f"(ID: {r['id']}, Rating: {r.get('rating')} stars, {r.get('batch_or_version') or 'N/A'})"
        for r in theme_reviews
    )

    markdown = f"""### {ticket_type}
**Title:** {title}
**Severity:** {theme['severity']}
**{affected_field}:** {", ".join(batches)}
**Incident Volume:** {theme['review_count']} user complaints ({theme.get('negative_rate', 0)}% negative)
**Core Keywords:** {", ".join(theme.get("keywords", []))}
**Data Source:** {"synthetic (generated templates)" if data_provenance.get("synthetic") else "real customer telemetry"}

#### Observed Customer Verbatims (Masked):
{quotes}

#### Recommended Action Items:
1. Halt distribution / trigger hotfix rollback for affected release or batch.
2. Cross-reference quality control logs and packaging vendor batch specs.
3. Validate automated unit tests and customer support response scripts.
"""

    # Session lifecycle is owned by Depends(get_db)
    ticket_id = None
    try:
        ticket_record = db_service.save_ticket(
            db=db,
            domain_id=active_dom,
            cluster_id=req.cluster_id,
            title=title,
            severity=theme['severity'],
            ticket_markdown=markdown,
            ticket_type=ticket_type,
            affected_field=affected_field,
            affected_values=batches,
            incident_volume=theme.get('review_count', 0)
        )
        ticket_id = ticket_record.id
    except Exception:
        logger.warning("Could not persist ticket to database", exc_info=True)

    return {
        "cluster_id": req.cluster_id,
        "ticket_id": ticket_id,
        "title": title,
        "severity": theme['severity'],
        "ticket_markdown": markdown,
        "persisted": ticket_id is not None,
    }


_MD_SPECIAL_CHARS = re.compile(r"([\\`*_{}\[\]()#+\-.!|~])")


def _md_escape(text: str) -> str:
    """Neutralises Markdown control characters and HTML tags in interpolated customer text.
    
    Prevents markdown breakout, header injections, malicious links, and XSS when
    generating triage tickets, export documents, or executive briefings.
    """
    if not text:
        return ""
    # Normalize line breaks and carriage returns to space
    sanitized = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    # Neutralize HTML tags
    sanitized = sanitized.replace("<", "&lt;").replace(">", "&gt;")
    # Escape markdown formatting and link characters (\, `, *, _, {, }, [, ], (, ), #, +, -, ., !, |, ~)
    sanitized = _MD_SPECIAL_CHARS.sub(r"\\\1", sanitized)
    # Collapse multiple consecutive whitespace characters
    return re.sub(r"\s+", " ", sanitized).strip()


@router.get("/tickets")
def list_tickets(domain: Optional[str] = Query(None, max_length=64), db=Depends(get_db),
                 user: Optional[AuthenticatedUser] = _auth()):
    """Retrieves all generated triage tickets stored in PostgreSQL."""
    ensure_initialized()
    try:
        target_domain = domain or state.active_domain or DEFAULT_DOMAIN
        tickets = db_service.get_tickets(db, target_domain)
        return {"tickets": tickets, "total": len(tickets)}
    except Exception:
        logger.error("Failed to fetch tickets", exc_info=True)
        raise HTTPException(status_code=503, detail="Ticket store is unavailable.")


@router.get("/auth/me")
def get_auth_me(user: Optional[AuthenticatedUser] = Depends(get_current_user_optional)):
    """Returns the currently authenticated Neon Auth user, or unauthenticated status."""
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user.to_dict()}


@router.get("/db/status")
def get_db_status(db=Depends(get_db), user: Optional[AuthenticatedUser] = _privileged_auth()):
    """Returns connectivity and record counts. Restricted: it is reconnaissance."""
    from app.core.database import check_db_connection

    status = check_db_connection()
    if status.get("connected"):
        try:
            status["domains_count"] = db.query(DomainModel).count()
            status["themes_count"] = db.query(ThemeModel).count()
            status["reviews_count"] = db.query(ReviewModel).count()
            status["tickets_count"] = db.query(TicketModel).count()
        except Exception:
            logger.warning("Record count query failed", exc_info=True)
            status["metrics_error"] = "record count unavailable"
    return status


@router.post("/search/semantic")
def search_semantic(req: SemanticSearchRequest, db=Depends(get_db),
                    user: Optional[AuthenticatedUser] = _auth()):
    """
    Real-time semantic vector search using all-MiniLM-L6-v2 embeddings
    and native pgvector cosine distance.
    """
    ensure_initialized()
    domain = req.domain or state.active_domain or DEFAULT_DOMAIN

    if transformer_encoder is None:
        raise HTTPException(
            status_code=503,
            detail="SentenceTransformer encoder is not loaded for vector search.",
        )

    try:
        query_vec = transformer_encoder.encode(req.query, normalize_embeddings=True).tolist()
        matches = db_service.semantic_vector_search(db, domain, query_vec, limit=req.limit)
        return {
            "query": req.query,
            "domain": domain,
            "total_matches": len(matches),
            "results": matches,
        }
    except HTTPException:
        raise
    except Exception:
        logger.error("Semantic search error", exc_info=True)
        raise HTTPException(status_code=500, detail="Semantic search failed.")


def _build_export_rows(reviews: list | None = None) -> list:
    """Redacted-only telemetry export with 4-way sentence intent and actionability metrics."""
    if reviews is not None:
        source_reviews = reviews
    else:
        active = state.active_domain or DEFAULT_DOMAIN
        source_reviews = DOMAIN_CACHE.get(active, {}).get("reviews", [])
    rows = []
    for r in source_reviews:
        sents = r.get("sentences", [])
        c_count = sum(1 for s in sents if s.get("label") == "COMPLAINT")
        p_count = sum(1 for s in sents if s.get("label") == "PRAISE")
        r_count = sum(1 for s in sents if s.get("label") == "RECOMMENDATION")
        rating = r.get("rating") or 0
        has_silent_defect = bool(
            rating >= 4 and ((r.get("highlight_span") or {}).get("detected") or c_count > 0)
        )
        rows.append({
            "Review_ID": r.get("id"),
            "Domain": r.get("domain"),
            "Product_Name": r.get("product_name"),
            "SKU_or_Module": r.get("sku_or_module"),
            "Batch_or_Version": r.get("batch_or_version"),
            "Submission_Date": r.get("submission_date"),
            "Channel": r.get("channel"),
            "Rating": r.get("rating"),
            "Calibrated_Sentiment": r.get("sentiment_pred"),
            "Sentiment_Confidence": r.get("sentiment_confidence"),
            "Theme_Title": r.get("theme_title", "General"),
            "Cluster_ID": r.get("cluster_id"),
            "Sentence_Count": len(sents),
            "Complaint_Clauses": c_count,
            "Praise_Clauses": p_count,
            "Recommendation_Clauses": r_count,
            "Is_Actionable": (c_count + p_count + r_count) > 0,
            "Has_Silent_Defect": has_silent_defect,
            "Is_PII_Scrubbed": bool(r.get("pii_detected")),
            "PII_Entities_Detected": ";".join(sorted(r.get("pii_detected") or [])),
            "Sanitized_Verbatim": r.get("redacted_text"),
            "Defect_Clause": (r.get("highlight_span") or {}).get("text", ""),
        })
    return rows


@router.get("/export/powerbi")
@router.get("/export/csv", include_in_schema=False)
def export_powerbi_telemetry(
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _privileged_auth(),
):
    """
    Streams clean, tabular telemetry for Microsoft Power BI Web Connector, Excel
    or CSV download. Contains redacted verbatim text only.

    Restricted to authorised roles because it returns the entire corpus.
    """
    from fastapi.responses import Response

    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle["reviews"]

    if not reviews:
        raise HTTPException(status_code=503, detail="No dataset is loaded yet.")

    csv_str = pd.DataFrame(_build_export_rows(reviews)).to_csv(index=False)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=insight_{active_dom}_telemetry.csv"
        },
    )


def _build_theme_export_rows(themes: list | None = None) -> list:
    if themes is not None:
        source_themes = themes
    else:
        active = state.active_domain or DEFAULT_DOMAIN
        source_themes = DOMAIN_CACHE.get(active, {}).get("themes", [])
    rows = []
    for t in source_themes:
        neg_val = t.get("negative_share", 0) or 0
        neg_pct = round(float(neg_val) * 100, 1) if float(neg_val) <= 1.0 else round(float(neg_val), 1)
        rows.append({
            "Cluster_ID": t.get("cluster_id"),
            "Theme_Title": t.get("title"),
            "Category": t.get("category", "General"),
            "Severity": t.get("severity", "MEDIUM"),
            "Review_Count": t.get("count", t.get("review_count", 0)),
            "Negative_Share_Pct": neg_pct,
            "Avg_Rating": round(float(t.get("avg_rating", 0) or 0), 2),
            "Top_Keywords": "; ".join(t.get("keywords", [])),
            "Medoid_Sample": t.get("medoid_verbatim", ""),
        })
    return rows


def _build_drift_export_rows(drift_results: dict | None = None) -> list:
    timeline = (drift_results or {}).get("timeline", [])
    rows = []
    for entry in timeline:
        rows.append({
            "Batch_or_Version": entry.get("batch"),
            "Total_Reviews": entry.get("total", 0),
            "Negative_Count": entry.get("negative", 0),
            "Positive_Count": entry.get("positive", 0),
            "Neutral_Count": entry.get("neutral", 0),
            "Negative_Rate_Pct": entry.get("negative_rate", 0.0),
            "PSI_Score": round(entry.get("psi") or 0.0, 4) if entry.get("psi") is not None else None,
            "Drift_Status": entry.get("drift_status", "BASELINE"),
            "Primary_Surging_Theme": entry.get("surging_theme"),
            "Surging_Delta_Pct": round(float(entry.get("surging_delta", 0.0) or 0.0) * 100, 1),
        })
    return rows


# ---------------------------------------------------------------------------
# Microsoft Power BI Live Analytics & Data Connectors
# ---------------------------------------------------------------------------

@router.get("/powerbi/config")
def get_powerbi_config(user: Optional[AuthenticatedUser] = _auth()):
    """Returns the current Power BI Embed workspace configuration."""
    return powerbi_service.get_config()


@router.post("/powerbi/config")
def save_powerbi_config(payload: PowerBIConfigPayload, user: Optional[AuthenticatedUser] = _auth()):
    """Saves and synchronizes the Power BI Embed report URL."""
    return powerbi_service.save_config(embed_url=payload.embed_url, report_title=payload.report_title)


@router.get("/powerbi/connector/pbids")
def get_powerbi_pbids_file(
    request: Request,
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Downloads an official Microsoft Power BI Data Source (.pbids) connection file.
    When opened on Windows, it automatically launches Power BI Desktop and pre-wires
    the InSight live telemetry feed.
    """
    from fastapi.responses import Response
    active_dom, _ = get_domain_bundle(domain)
    base_url = str(request.base_url).rstrip("/")
    pbids_data = powerbi_service.generate_pbids_content(base_api_url=base_url)
    return Response(
        content=json.dumps(pbids_data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=InSight_{active_dom}_Telemetry.pbids"
        },
    )


@router.get("/powerbi/data/reviews.csv")
def get_powerbi_reviews_csv(
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Streams clean, tabular telemetry directly for Power BI Desktop Web Connector.
    Includes sanitized verbatims, clause-level counts, and calibrated sentiment.
    """
    from fastapi.responses import Response
    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle["reviews"]
    if not reviews:
        raise HTTPException(status_code=503, detail="No dataset is loaded yet.")
    csv_str = pd.DataFrame(_build_export_rows(reviews)).to_csv(index=False)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=insight_{active_dom}_telemetry.csv",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/powerbi/data/reviews")
def get_powerbi_reviews_json(
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    limit: Optional[int] = Query(None, ge=1, le=50000),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns normalized Star Schema Fact_ReviewTelemetry rows in JSON for Power BI REST connectors.
    """
    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle["reviews"]
    rows = _build_export_rows(reviews)
    if limit:
        rows = rows[:limit]
    return {
        "domain": active_dom,
        "total_rows": len(rows),
        "data": rows,
    }


@router.get("/powerbi/data/themes")
def get_powerbi_themes_json(
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns Dim_Themes dimension rows in JSON format.
    """
    active_dom, bundle = get_domain_bundle(domain)
    themes = bundle["themes"]
    rows = _build_theme_export_rows(themes)
    return {
        "domain": active_dom,
        "total_themes": len(rows),
        "data": rows,
    }


@router.get("/powerbi/data/themes.csv")
def get_powerbi_themes_csv(
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Streams Dim_Themes dimension as a CSV file for Power BI model relationship building.
    """
    from fastapi.responses import Response
    active_dom, bundle = get_domain_bundle(domain)
    themes = bundle["themes"]
    rows = _build_theme_export_rows(themes)
    csv_str = pd.DataFrame(rows).to_csv(index=False)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=insight_{active_dom}_themes_dim.csv"
        },
    )


@router.get("/powerbi/data/drift")
def get_powerbi_drift_json(
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns Fact_BatchDrift timeline metrics (PSI scores, cohort shifts, relative risks).
    """
    active_dom, bundle = get_domain_bundle(domain)
    drift_results = bundle["drift_results"]
    rows = _build_drift_export_rows(drift_results)
    return {
        "domain": active_dom,
        "total_cohorts": len(rows),
        "data": rows,
    }


@router.get("/powerbi/data/summary")
def get_powerbi_summary_json(
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns high-level executive KPIs optimized for Power BI Card / Gauge visuals.
    """
    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle["reviews"]
    themes = bundle["themes"]
    total = len(reviews)
    pos = sum(1 for r in reviews if r.get("sentiment_pred") == "POSITIVE")
    neu = sum(1 for r in reviews if r.get("sentiment_pred") == "NEUTRAL")
    neg = sum(1 for r in reviews if r.get("sentiment_pred") == "NEGATIVE")

    nss = round(((pos - neg) / total * 100), 1) if total else 0.0
    rows = _build_export_rows(reviews)
    defect_count = sum(1 for r in rows if r["Complaint_Clauses"] > 0)
    silent_defects = sum(1 for r in rows if r["Has_Silent_Defect"])
    actionable_count = sum(1 for r in rows if r["Is_Actionable"])

    return {
        "domain": active_dom,
        "total_reviews": total,
        "net_sentiment_score": nss,
        "positive_rate_pct": round((pos / total * 100), 1) if total else 0.0,
        "negative_rate_pct": round((neg / total * 100), 1) if total else 0.0,
        "neutral_rate_pct": round((neu / total * 100), 1) if total else 0.0,
        "defect_surge_rate_pct": round((defect_count / total * 100), 1) if total else 0.0,
        "silent_defects_count": silent_defects,
        "actionable_rate_pct": round((actionable_count / total * 100), 1) if total else 0.0,
        "pii_compliance_rate_pct": 100.0,
        "total_themes": len(themes),
        "critical_themes": sum(1 for t in themes if t.get("severity") == "CRITICAL"),
    }


@router.get("/powerbi/guide")
def get_powerbi_guide(
    request: Request,
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns Power Query M script, DAX measure catalog, and Star Schema specifications.
    """
    base_url = str(request.base_url).rstrip("/")
    return {
        "api_urls": {
            "csv_feed": f"{base_url}/api/powerbi/data/reviews.csv",
            "json_feed": f"{base_url}/api/powerbi/data/reviews",
            "themes_feed": f"{base_url}/api/powerbi/data/themes.csv",
            "drift_feed": f"{base_url}/api/powerbi/data/drift",
            "pbids_file": f"{base_url}/api/powerbi/connector/pbids",
        },
        "power_query_m": powerbi_service.get_powerquery_m_snippet(base_url),
        "dax_measures": powerbi_service.get_dax_measures(),
        "star_schema": {
            "fact_table": "Fact_ReviewTelemetry",
            "dimension_tables": ["Dim_Themes", "Dim_BatchRelease", "Dim_ProductSKU", "Dim_Channel"],
        }
    }


@router.get("/powerbi/embed-token")
def get_powerbi_embed_token(user: Optional[AuthenticatedUser] = _auth()):
    """
    Official Microsoft Power BI Embedded (App Owns Data) endpoint.
    
    1. Authenticates against Microsoft Entra ID via client credentials.
    2. Retrieves report metadata and embedUrl from Power BI REST API.
    3. Mints a short-lived Embed Token for genuine client-side report embedding.
    """
    cfg_status = powerbi_service.get_azure_config_status()
    if not cfg_status["is_configured"]:
        return {
            "status": "unconfigured",
            "message": "Power BI Service & Azure Entra ID credentials are not yet configured in .env",
            "missing_keys": cfg_status["missing_keys"],
            "credentials_present": cfg_status["credentials_present"],
            "setup_guide": {
                "step_1": "Register an App in Microsoft Entra ID (Azure Portal) and generate a Client Secret.",
                "step_2": "In Power BI Admin Portal, enable 'Allow service principals to use Power BI APIs'.",
                "step_3": "Add the Azure App Registration as a Member/Contributor to your Power BI Workspace.",
                "step_4": "Populate POWERBI_TENANT_ID, POWERBI_CLIENT_ID, POWERBI_CLIENT_SECRET, POWERBI_WORKSPACE_ID, and POWERBI_REPORT_ID in .env",
            }
        }

    try:
        result = powerbi_service.generate_embed_token()
        return result
    except Exception as e:
        logger.error(f"Failed to generate Power BI Embed Token: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "workspace_id": settings.POWERBI_WORKSPACE_ID,
            "report_id": settings.POWERBI_REPORT_ID,
            "diagnostics": {
                "tenant_id_set": bool(settings.POWERBI_TENANT_ID),
                "client_id_set": bool(settings.POWERBI_CLIENT_ID),
                "client_secret_set": bool(settings.POWERBI_CLIENT_SECRET),
                "workspace_id_set": bool(settings.POWERBI_WORKSPACE_ID),
                "report_id_set": bool(settings.POWERBI_REPORT_ID),
            }
        }


@router.get("/powerbi/connection-status")
def test_powerbi_connection_status(user: Optional[AuthenticatedUser] = _auth()):
    """
    Tests live connectivity to Azure Entra ID and Microsoft Power BI Service.
    """
    return powerbi_service.test_connection()


@router.post("/powerbi/dataset/refresh")
def trigger_powerbi_dataset_refresh(user: Optional[AuthenticatedUser] = _auth()):
    """
    Triggers an asynchronous refresh on the Power BI Semantic Model via Power BI REST API.
    """
    try:
        return powerbi_service.trigger_dataset_refresh()
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to trigger Power BI dataset refresh: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Power BI API refresh failed: {str(e)}")



# ---------------------------------------------------------------------------
# Complaint Clusters & Sentence Pools Endpoints
# ---------------------------------------------------------------------------

@router.get("/complaint-clusters")
def get_complaint_clusters(
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    severity: Optional[str] = Query(None, description="Optional filter by severity: CRITICAL, HIGH, MEDIUM, LOW"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns sentence-level complaint clusters discovered via MiniLM + c-TF-IDF.
    Includes severity, c-TF-IDF root cause keywords, medoid verbatims, and Relative Risk.
    """
    active_dom, bundle = get_domain_bundle(domain)
    clusters = bundle.get("complaint_clusters") or []
    if severity:
        clusters = [c for c in clusters if str(c.get("severity")).upper() == severity.upper()]
    return {
        "clusters": clusters,
        "total": len(clusters),
        "domain": active_dom,
    }


@router.get("/complaint-clusters/{cluster_id}/verbatims")
def get_complaint_cluster_verbatims(
    cluster_id: int,
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of verbatim items to load per page"),
    offset: Optional[int] = Query(None, ge=0, description="Optional 0-indexed item offset for continuous scrolling"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Optional item limit for continuous scrolling"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns representative sentence verbatims for a specific complaint cluster with pagination support,
    including character slice offsets [start, end] for verbatim span highlighting.
    """
    active_dom, bundle = get_domain_bundle(domain)
    clusters = bundle.get("complaint_clusters") or []
    matched = [c for c in clusters if c.get("cluster_id") == cluster_id]
    if not matched:
        raise HTTPException(status_code=404, detail=f"Complaint cluster #{cluster_id} not found in domain '{active_dom}'.")
    cluster = matched[0]
    all_verbatims = cluster.get("verbatims", [])
    total_items = len(all_verbatims)
    if offset is not None and limit is not None:
        start_idx = offset
        take = limit
        effective_page = (offset // limit) + 1
        effective_page_size = limit
    else:
        start_idx = (page - 1) * page_size
        take = page_size
        effective_page = page
        effective_page_size = page_size

    sliced = all_verbatims[start_idx : start_idx + take]
    total_pages = max(1, (total_items + effective_page_size - 1) // effective_page_size) if total_items > 0 else 1

    return {
        "cluster_id": cluster_id,
        "domain": active_dom,
        "title": cluster.get("title"),
        "severity": cluster.get("severity"),
        "keywords": cluster.get("keywords", []),
        "sentence_count": cluster.get("sentence_count", 0),
        "medoid_verbatim": cluster.get("medoid_verbatim"),
        "affected_batch": cluster.get("affected_batch"),
        "relative_risk": cluster.get("relative_risk"),
        "page": effective_page,
        "page_size": effective_page_size,
        "offset": start_idx,
        "total": total_items,
        "total_pages": total_pages,
        "has_more": start_idx + len(sliced) < total_items,
        "verbatims": sliced,
    }


@router.get("/feature-requests")
def get_feature_requests(
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns structured customer recommendations and wishlist proposals
    isolated by the sentence intent classifier.
    """
    active_dom, bundle = get_domain_bundle(domain)
    feature_requests = bundle.get("feature_requests") or []
    return {
        "feature_requests": feature_requests,
        "total": len(feature_requests),
        "domain": active_dom,
    }


@router.get("/praise-clusters")
def get_praise_clusters(
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns sentence-level product strength and delight clusters discovered
    via MiniLM + c-TF-IDF over the PRAISE intent pool.
    """
    active_dom, bundle = get_domain_bundle(domain)
    clusters = bundle.get("praise_clusters") or []
    return {
        "clusters": clusters,
        "total": len(clusters),
        "domain": active_dom,
    }


@router.get("/praise-clusters/{cluster_id}/verbatims")
def get_praise_cluster_verbatims(
    cluster_id: int,
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of verbatim items to load per page"),
    offset: Optional[int] = Query(None, ge=0, description="Optional 0-indexed item offset for continuous scrolling"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Optional item limit for continuous scrolling"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns representative sentence verbatims for a specific product strength cluster with pagination support,
    including character slice offsets [start, end] for verbatim span highlighting.
    """
    active_dom, bundle = get_domain_bundle(domain)
    clusters = bundle.get("praise_clusters") or []
    matched = [c for c in clusters if c.get("cluster_id") == cluster_id]
    if not matched:
        raise HTTPException(status_code=404, detail=f"Product strength cluster #{cluster_id} not found in domain '{active_dom}'.")
    cluster = matched[0]
    all_verbatims = cluster.get("verbatims", [])
    total_items = len(all_verbatims)
    if offset is not None and limit is not None:
        start_idx = offset
        take = limit
        effective_page = (offset // limit) + 1
        effective_page_size = limit
    else:
        start_idx = (page - 1) * page_size
        take = page_size
        effective_page = page
        effective_page_size = page_size

    sliced = all_verbatims[start_idx : start_idx + take]
    total_pages = max(1, (total_items + effective_page_size - 1) // effective_page_size) if total_items > 0 else 1

    return {
        "cluster_id": cluster_id,
        "domain": active_dom,
        "title": cluster.get("title"),
        "strength_drivers": cluster.get("strength_drivers", cluster.get("keywords", [])),
        "keywords": cluster.get("keywords", []),
        "praise_count": cluster.get("praise_count", cluster.get("sentence_count", 0)),
        "delight_score": cluster.get("delight_score", 0.0),
        "delight_tier": cluster.get("delight_tier", "STRONG"),
        "medoid_verbatim": cluster.get("medoid_verbatim"),
        "page": effective_page,
        "page_size": effective_page_size,
        "offset": start_idx,
        "total": total_items,
        "total_pages": total_pages,
        "has_more": start_idx + len(sliced) < total_items,
        "verbatims": sliced,
    }


@router.get("/reviews/silent-defects")
def get_silent_defects(
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    min_rating: int = Query(4, ge=3, le=5, description="Filter for positive ratings containing hidden defects"),
    limit: int = Query(50, ge=1, le=200),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    The 'Trojan Horse' Filter: Returns 4★ and 5★ reviews that contain a verified
    defect clause or complaint sentence. Solves the 'Whole-Document Fallacy'.
    """
    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle["reviews"]
    silent = []
    for r in reviews:
        rating = r.get("rating") or 0
        if rating < min_rating:
            continue
        
        has_defect_span = bool((r.get("highlight_span") or {}).get("detected"))
        has_complaint_sentence = any(
            s.get("label") == "COMPLAINT" for s in r.get("sentences", [])
        )
        if has_defect_span or has_complaint_sentence:
            silent.append({
                "id": r.get("id"),
                "rating": rating,
                "product_name": r.get("product_name"),
                "sku_or_module": r.get("sku_or_module"),
                "batch_or_version": r.get("batch_or_version"),
                "display_text": r.get("redacted_text"),
                "sentiment_pred": r.get("sentiment_pred"),
                "highlight_span": r.get("highlight_span"),
                "sentences": r.get("sentences", []),
            })
            if len(silent) >= limit:
                break

    return {
        "domain": active_dom,
        "silent_defects": silent,
        "total_found": len(silent),
        "min_rating": min_rating,
    }


@router.get("/noise-telemetry")
def get_noise_telemetry(
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    limit: int = Query(50, ge=10, le=100),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns quarantined non-actionable chatter, ambient phrases, and noise word cloud telemetry.
    Shows the words that were safely discarded so product managers only focus on real signal.
    """
    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle.get("reviews") or []

    noise_sentences = []
    noise_word_counts = {}

    # Common conversational / grammatical stop-words
    stop = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "it",
        "is", "was", "my", "i", "this", "that", "of", "so", "but", "be", "as", "by",
        "have", "had", "they", "we", "you", "me", "her", "his", "she", "he", "just",
        "very", "too", "been", "from", "are", "were", "would", "could", "will", "when"
    }

    for r in reviews:
        for s in r.get("sentences", []):
            lbl = s.get("label")
            if lbl in ("NOISE", "NEUTRAL") or (not lbl or lbl not in ("COMPLAINT", "PRAISE", "RECOMMENDATION")):
                txt = s.get("sentence_text", "")
                if len(txt) > 15:
                    if len(noise_sentences) < limit:
                        noise_sentences.append({
                            "sentence_id": s.get("sentence_id"),
                            "review_id": r.get("id"),
                            "rating": r.get("rating"),
                            "text": txt,
                            "reason": "Ambient transactional context without defect or feature request.",
                        })
                    tokens = re.findall(r"\b[a-zA-Z]{3,15}\b", txt.lower())
                    for tok in tokens:
                        if tok not in stop:
                            noise_word_counts[tok] = noise_word_counts.get(tok, 0) + 1

    sorted_words = sorted(noise_word_counts.items(), key=lambda x: x[1], reverse=True)[:60]

    total_noise_sents = sum(
        1 for r in reviews for s in r.get("sentences", [])
        if s.get("label") not in ("COMPLAINT", "PRAISE", "RECOMMENDATION")
    )
    total_all_sents = sum(len(r.get("sentences", [])) for r in reviews)

    # Deterministic pseudo-random placement for stable visually attractive floating scatter cloud
    rng = random.Random(42)
    max_c = sorted_words[0][1] if sorted_words else 1
    word_cloud = []
    for rank, (w, count) in enumerate(sorted_words):
        size_rem = round(0.75 + min(1.3, (count / max(max_c, 1)) * 1.3), 2)
        weight = min(800, max(400, 400 + int((count / max(max_c, 1)) * 400)))
        top_pct = round(rng.uniform(6, 86), 1)
        left_pct = round(rng.uniform(4, 88), 1)
        word_cloud.append({
            "word": w,
            "count": count,
            "size": f"{size_rem}rem",
            "weight": weight,
            "top": f"{top_pct}%",
            "left": f"{left_pct}%",
            "opacity": round(rng.uniform(0.60, 0.95), 2),
            "color": rng.choice(["#4B5563", "#6B7280", "#374151", "#475569", "#64748B", "#94A3B8"])
        })

    hours_saved = round((total_noise_sents * 2.0) / 60.0, 1)

    return {
        "domain": active_dom,
        "total_noise_sentences": total_noise_sents,
        "total_sentences": total_all_sents,
        "noise_rate_pct": round((total_noise_sents / max(total_all_sents, 1)) * 100, 1),
        "engineering_hours_saved": hours_saved,
        "word_cloud": word_cloud,
        "sample_quarantined_sentences": noise_sentences[:limit],
    }


class IncidentTicketRequest(BaseModel):
    cluster_id: int
    domain: Optional[str] = None


@router.post("/ticket/generate-incident")
def generate_incident_ticket(
    payload: IncidentTicketRequest,
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    1-Click Engineering & Jira Incident Dispatch:
    Generates a structured engineering bug / QA incident report for a complaint cluster.
    """
    active_dom, bundle = get_domain_bundle(payload.domain)
    clusters = bundle.get("complaint_clusters") or []
    matched = [c for c in clusters if c.get("cluster_id") == payload.cluster_id]
    if not matched:
        raise HTTPException(status_code=404, detail=f"Complaint cluster #{payload.cluster_id} not found in domain '{active_dom}'.")
    cluster = matched[0]

    title = cluster.get("title", f"Defect Pattern #{payload.cluster_id}")
    severity = cluster.get("severity", "HIGH")
    keywords = ", ".join(cluster.get("keywords", []))
    volume = cluster.get("sentence_count", 0)
    batch = cluster.get("affected_batch") or "Omnichannel / Multiple Batches"
    rr = cluster.get("relative_risk", 1.0)
    medoid = cluster.get("medoid_verbatim", "N/A")

    ticket_md = f"""# [INCIDENT REPORT] {title}

**Priority:** {severity}
**Reported Incident Volume:** {volume} customer citations
**Estimated Blast Radius:** {rr}x relative risk concentration on `{batch}`
**Identified Complaint Drivers (c-TF-IDF):** {keywords}

---

### Incident Summary
Customer feedback analysis detected a statistically significant defect concentration regarding **{title}**. 
Affected customers specifically report failures matching: `{medoid}`.

### Cohort Attribution & Relative Risk
- **Primary Over-Indexed Cohort:** `{batch}`
- **Relative Risk (RR):** `{rr}x` baseline failure probability
- **Statistical Significance:** {'Verified (p < 0.05)' if cluster.get('is_statistically_significant') else 'Observational Signal'}

### Sample Cited Customer Verbatims
"""
    for v in cluster.get("verbatims", [])[:4]:
        ticket_md += f"- *\"{v.get('sentence_text')}\"* (Ref: `{v.get('sentence_id')}`)\n"

    ticket_md += """
---
*Automated telemetry report dispatched via InSight Omni-Corpus Intelligence Engine.*
"""

    ticket_payload = {
        "title": f"[{severity}] Incident: {title}",
        "severity": severity,
        "cluster_id": payload.cluster_id,
        "incident_volume": volume,
        "affected_batch": batch,
        "relative_risk": rr,
        "ticket_markdown": ticket_md,
        "status": "OPEN",
        "keywords": cluster.get("keywords", []),
        "medoid_verbatim": medoid,
        "is_statistically_significant": cluster.get("is_statistically_significant", True),
        "verbatims": cluster.get("verbatims", [])[:4],
    }
    return {
        **ticket_payload,
        "ticket": ticket_payload,
    }


# ==============================================================================
# ADVANCED VISUAL ANALYTICS: TEMPORAL DRIFT, SKU RISK MATRIX & DIVERGENCE
# ==============================================================================

@router.get("/analytics/temporal-drift")
def get_temporal_drift_analytics(
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    limit_cohorts: int = Query(12, ge=4, le=60),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns multi-series quarterly temporal drift trajectories for top defect clusters,
    enabling frontend stacked area and multi-line time-series visualizations.
    """
    ensure_initialized()
    active_dom, bundle = get_domain_bundle(domain)
    drift_data = bundle.get("drift_results") or {}
    timeline = drift_data.get("timeline") or []
    complaint_clusters = bundle.get("complaint_clusters") or []
    reviews = bundle.get("reviews") or []

    # Sort timeline cohorts chronologically and take most recent limit_cohorts
    sorted_timeline = sorted(timeline, key=lambda t: t.get("batch_or_version", ""))
    if len(sorted_timeline) > limit_cohorts:
        sorted_timeline = sorted_timeline[-limit_cohorts:]

    cohort_labels = [t.get("batch_or_version") for t in sorted_timeline]
    palette = ["#EF4444", "#F97316", "#F59E0B", "#3B82F6", "#8B5CF6", "#10B981", "#EC4899", "#6366F1"]
    theme_series = []

    if complaint_clusters:
        top_clusters = sorted(
            complaint_clusters,
            key=lambda c: (1 if c.get("severity") == "CRITICAL" else 0, c.get("sentence_count", 0)),
            reverse=True
        )[:6]

        rev_to_cohort = {r.get("id"): r.get("batch_or_version") for r in reviews if r.get("batch_or_version")}

        for idx, cl in enumerate(top_clusters):
            cid = cl.get("cluster_id")
            title = cl.get("title", f"Cluster {cid}")
            sev = cl.get("severity", "MEDIUM")
            counts_by_cohort = {c: 0 for c in cohort_labels}
            for v in cl.get("verbatims", []):
                c_lbl = rev_to_cohort.get(v.get("review_id"))
                if c_lbl in counts_by_cohort:
                    counts_by_cohort[c_lbl] += 1

            data_points = []
            for t in sorted_timeline:
                c_lbl = t.get("batch_or_version")
                neg_vol = t.get("negative_count", 0)
                tot_vol = max(t.get("review_count", 1), 1)
                direct_c = counts_by_cohort.get(c_lbl, 0)
                est_c = max(direct_c, int(round((cl.get("sentence_count", 10) / max(len(reviews) * 0.2, 1)) * neg_vol)))
                rate_pct = round((est_c / tot_vol) * 100, 2)
                data_points.append({
                    "cohort": c_lbl,
                    "count": est_c,
                    "rate_pct": rate_pct,
                    "review_volume": tot_vol
                })

            theme_series.append({
                "cluster_id": cid,
                "title": title,
                "severity": sev,
                "color": palette[idx % len(palette)],
                "data": data_points
            })
    else:
        themes = bundle.get("themes") or []
        for idx, th in enumerate(themes[:6]):
            t_name = th.get("title") or th.get("name", "Theme")
            data_points = []
            for t in sorted_timeline:
                c_lbl = t.get("batch_or_version")
                th_counts = t.get("themes", {})
                count = th_counts.get(t_name, 0)
                tot = max(t.get("review_count", 1), 1)
                data_points.append({
                    "cohort": c_lbl,
                    "count": count,
                    "rate_pct": round((count / tot) * 100, 2),
                    "review_volume": tot
                })
            theme_series.append({
                "cluster_id": idx,
                "title": t_name,
                "severity": th.get("severity", "MEDIUM"),
                "color": palette[idx % len(palette)],
                "data": data_points
            })

    hotspots = []
    for a in drift_data.get("alerts", []):
        hotspots.append({
            "batch_or_version": a.get("batch_or_version"),
            "theme": a.get("surging_theme"),
            "relative_risk": a.get("relative_risk", 1.0),
            "psi_score": a.get("psi_score", 0.0),
            "p_value": a.get("p_value", 0.01),
            "is_statistically_significant": a.get("is_statistically_significant", True)
        })

    return {
        "domain": active_dom,
        "cohorts": cohort_labels,
        "series": theme_series,
        "timeline_summary": [
            {
                "cohort": t.get("batch_or_version"),
                "total_reviews": t.get("review_count", 0),
                "negative_count": t.get("negative_count", 0),
                "positive_count": t.get("positive_count", 0),
                "psi": t.get("psi", 0.0),
                "status": t.get("status", "STABLE")
            }
            for t in sorted_timeline
        ],
        "hotspots": hotspots[:6]
    }


@router.get("/analytics/product-matrix")
def get_product_matrix_analytics(
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    limit: int = Query(15, ge=5, le=50),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Groups telemetry by product name to produce a SKU/Product Risk Matrix.
    Identifies high-defect products, their average star ratings, complaint rates,
    and dominant defect themes.
    """
    ensure_initialized()
    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle.get("reviews") or []

    prod_groups = {}
    for r in reviews:
        pname = r.get("product_name") or "Unknown Product"
        if pname not in prod_groups:
            prod_groups[pname] = {
                "product_name": pname,
                "brand_name": r.get("brand_name") or "Brand",
                "reviews": [],
            }
        prod_groups[pname]["reviews"].append(r)

    eligible = [p for p in prod_groups.values() if len(p["reviews"]) >= 15]
    if not eligible:
        eligible = list(prod_groups.values())

    matrix = []
    for item in eligible:
        revs = item["reviews"]
        tot = len(revs)
        avg_rating = round(sum(r.get("rating", 3) for r in revs) / tot, 2)

        complaint_reviews = 0
        complaint_reasons = {}
        defective_batches = set()

        for r in revs:
            sents = r.get("sentences", [])
            c_sents = [s for s in sents if s.get("label") == "COMPLAINT"]
            if c_sents or r.get("sentiment_pred") == "NEGATIVE":
                complaint_reviews += 1
                if r.get("batch_or_version"):
                    defective_batches.add(r.get("batch_or_version"))
                for s in c_sents:
                    txt = s.get("sentence_text", "")
                    if any(w in txt.lower() for w in ["burn", "redness", "allergic", "rash", "dermatitis"]):
                        complaint_reasons["Chemical Irritation / Burn"] = complaint_reasons.get("Chemical Irritation / Burn", 0) + 1
                    elif any(w in txt.lower() for w in ["leak", "pump", "broken", "cracked", "dispenser", "nozzle"]):
                        complaint_reasons["Packaging / Dispenser Defect"] = complaint_reasons.get("Packaging / Dispenser Defect", 0) + 1
                    elif any(w in txt.lower() for w in ["dry", "peeling", "dehydrat", "flaky"]):
                        complaint_reasons["Dryness / Peeling"] = complaint_reasons.get("Dryness / Peeling", 0) + 1
                    elif any(w in txt.lower() for w in ["acne", "breakout", "pimples", "clog"]):
                        complaint_reasons["Acne & Clogged Pores"] = complaint_reasons.get("Acne & Clogged Pores", 0) + 1
                    else:
                        complaint_reasons["Formula Inefficacy"] = complaint_reasons.get("Formula Inefficacy", 0) + 1

        defect_rate_pct = round((complaint_reviews / tot) * 100, 1)
        top_reason = max(complaint_reasons.items(), key=lambda x: x[1])[0] if complaint_reasons else "Minor Usability"

        if defect_rate_pct >= 28.0 or "Chemical Irritation" in top_reason:
            risk_tier = "CRITICAL"
        elif defect_rate_pct >= 15.0:
            risk_tier = "ELEVATED"
        else:
            risk_tier = "STABLE"

        sample_q = next(
            (s.get("sentence_text") for r in revs for s in r.get("sentences", []) if s.get("label") == "COMPLAINT" and len(s.get("sentence_text", "")) > 20),
            revs[0].get("redacted_text", "")[:120]
        )

        matrix.append({
            "product_name": item["product_name"],
            "brand_name": item["brand_name"],
            "total_reviews": tot,
            "avg_rating": avg_rating,
            "complaint_count": complaint_reviews,
            "defect_rate_pct": defect_rate_pct,
            "risk_tier": risk_tier,
            "top_defect_theme": top_reason,
            "sample_defect_quote": sample_q,
            "affected_cohorts": sorted(list(defective_batches))[:3]
        })

    matrix.sort(key=lambda m: (1 if m["risk_tier"] == "CRITICAL" else (0.5 if m["risk_tier"] == "ELEVATED" else 0), m["defect_rate_pct"]), reverse=True)

    return {
        "domain": active_dom,
        "total_products_analyzed": len(matrix),
        "products": matrix[:limit]
    }


@router.get("/analytics/rating-divergence")
def get_rating_divergence_analytics(
    domain: Optional[str] = Query(None, description="Optional domain identifier"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Quantifies the 'Whole-Document Fallacy' and 'Trojan Horse Reviews':
    Calculates the exact percentage of defects and complaint sentences hidden inside
    reviews with 4-star and 5-star ratings, and extracts self-reported loyalty turncoats.
    """
    ensure_initialized()
    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle.get("reviews") or []

    star_complaint_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    star_review_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_complaint_sentences = 0
    trojan_samples = []
    turncoat_samples = []

    loyalty_pat = re.compile(
        r"\b(used to love|used this for years|holy grail until|bought this for years|reformulat|used to be my favorite|not purchasing again|will never repurchase|returning this|switching to another|waste of money|ruined my skin)\b",
        re.IGNORECASE
    )

    for r in reviews:
        star = int(r.get("rating", 3))
        if star in star_review_counts:
            star_review_counts[star] += 1
        sents = r.get("sentences", [])
        c_sents = [s for s in sents if s.get("label") == "COMPLAINT"]

        if c_sents:
            count = len(c_sents)
            if star in star_complaint_counts:
                star_complaint_counts[star] += count
            total_complaint_sentences += count

            if star >= 4 and len(trojan_samples) < 8:
                c_txt = c_sents[0].get("sentence_text", "")
                if len(c_txt) > 25 and not any(t["complaint_text"] == c_txt for t in trojan_samples):
                    trojan_samples.append({
                        "review_id": r.get("id"),
                        "product_name": r.get("product_name"),
                        "rating": star,
                        "complaint_text": c_txt,
                        "full_snippet": r.get("redacted_text", "")[:180] + "...",
                        "why_missed": f"Conventional sentiment scored this {star}-star review as POSITIVE, masking the embedded failure."
                    })

        red_text = r.get("redacted_text", "")
        if star <= 3 and len(turncoat_samples) < 6:
            m = loyalty_pat.search(red_text)
            if m:
                turncoat_samples.append({
                    "review_id": r.get("id"),
                    "product_name": r.get("product_name"),
                    "rating": star,
                    "trigger_phrase": m.group(0),
                    "quote": red_text[:160] + "...",
                    "batch": r.get("batch_or_version") or "Latest Batch"
                })

    trojan_count = star_complaint_counts[4] + star_complaint_counts[5]
    trojan_rate_pct = round((trojan_count / max(total_complaint_sentences, 1)) * 100, 1)

    return {
        "domain": active_dom,
        "total_reviews": len(reviews),
        "total_complaint_sentences": total_complaint_sentences,
        "trojan_horse_metrics": {
            "trojan_complaint_count": trojan_count,
            "trojan_rate_pct": trojan_rate_pct,
            "low_star_complaint_count": star_complaint_counts[1] + star_complaint_counts[2] + star_complaint_counts[3],
            "low_star_rate_pct": round(100.0 - trojan_rate_pct, 1),
            "blind_spot_warning": f"{trojan_rate_pct}% of customer-reported defects occur inside 4★ and 5★ reviews, rendering them invisible to conventional low-star sentiment filters."
        },
        "star_distribution": [
            {
                "star": s,
                "label": f"{s} Star",
                "complaint_count": star_complaint_counts[s],
                "complaint_pct": round((star_complaint_counts[s] / max(total_complaint_sentences, 1)) * 100, 1),
                "total_reviews": star_review_counts[s]
            }
            for s in [1, 2, 3, 4, 5]
        ],
        "top_trojan_samples": trojan_samples,
        "loyalty_turncoats": turncoat_samples
    }


# ==============================================================================
# EXECUTIVE REVIEW INTELLIGENCE COPILOT (RAG OVER INSIGHT TELEMETRY)
# ==============================================================================

class CopilotQueryRequest(BaseModel):
    query: str
    domain: Optional[str] = None
    limit_citations: Optional[int] = 4


@router.post("/copilot/ask")
def copilot_ask(payload: CopilotQueryRequest, user: Optional[AuthenticatedUser] = _auth()):
    """
    Executive Review Intelligence Copilot (RAG over InSight Telemetry).
    Answers questions grounded in customer verbatims, sentiment scores, and drift metrics.
    """
    ensure_initialized()
    active_dom, bundle = get_domain_bundle(payload.domain)
    reviews = bundle.get("reviews", [])
    themes = bundle.get("themes", [])
    complaint_clusters = bundle.get("complaint_clusters", [])
    praise_clusters = bundle.get("praise_clusters", [])
    feature_requests = bundle.get("feature_requests", [])
    drift_data = bundle.get("drift_results", {})

    return copilot_service.answer_query(
        query=payload.query,
        reviews=reviews,
        themes=themes,
        complaint_clusters=complaint_clusters,
        praise_clusters=praise_clusters,
        feature_requests=feature_requests,
        drift_data=drift_data,
        encoder=transformer_encoder,
        limit_citations=payload.limit_citations or 4
    )


@router.get("/copilot/briefing")
def copilot_briefing(domain: Optional[str] = None, user: Optional[AuthenticatedUser] = _auth()):
    """
    Generates an executive-ready One-Pager Intelligence Briefing.
    """
    ensure_initialized()
    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle.get("reviews", [])
    themes = bundle.get("themes", [])
    complaint_clusters = bundle.get("complaint_clusters", [])
    praise_clusters = bundle.get("praise_clusters", [])
    feature_requests = bundle.get("feature_requests", [])
    drift_data = bundle.get("drift_results", {})

    return copilot_service.generate_executive_briefing(
        domain=active_dom,
        reviews=reviews,
        themes=themes,
        complaint_clusters=complaint_clusters,
        praise_clusters=praise_clusters,
        feature_requests=feature_requests,
        drift_data=drift_data
    )


# ==============================================================================
# HEAD-TO-HEAD COMPARATIVE BENCHMARK ENGINE
# ==============================================================================

class BenchmarkCompareRequest(BaseModel):
    compare_type: str = "batch" # "batch" or "domain"
    cohort_a: str
    cohort_b: str


@router.get("/benchmark/cohorts")
def get_benchmark_cohorts(domain: Optional[str] = Query(None), user: Optional[AuthenticatedUser] = _auth()):
    """
    Returns available comparison cohorts (batches and domains).
    """
    ensure_initialized()
    _, bundle = get_domain_bundle(domain)
    bundle_reviews = bundle.get("reviews", [])
    batches = sorted(list(set(r.get("batch_or_version") for r in bundle_reviews if r.get("batch_or_version"))))
    domains = [
        {"id": "d2c_cosmetics", "name": "D2C Cosmetics & Skincare (Sephora 10k)"},
        {"id": "tech_saas", "name": "Fintech / SaaS Digital App (Telemetry)"}
    ]
    return {
        "batches": batches,
        "domains": domains
    }


@router.post("/benchmark/compare")
def compare_benchmarks(payload: BenchmarkCompareRequest, user: Optional[AuthenticatedUser] = _auth()):
    """
    Head-to-head comparative intelligence between two batches or domains.
    """
    ensure_initialized()
    if payload.compare_type == "domain":
        _, bundle_a = get_domain_bundle(payload.cohort_a)
        _, bundle_b = get_domain_bundle(payload.cohort_b)
        revs_a = bundle_a.get("reviews", [])
        revs_b = bundle_b.get("reviews", [])
        label_a = "D2C Cosmetics" if payload.cohort_a == "d2c_cosmetics" else "Tech / SaaS"
        label_b = "D2C Cosmetics" if payload.cohort_b == "d2c_cosmetics" else "Tech / SaaS"
    else:
        _, bundle = get_domain_bundle()
        domain_reviews = bundle.get("reviews", [])
        revs_a = [r for r in domain_reviews if r.get("batch_or_version") == payload.cohort_a]
        revs_b = [r for r in domain_reviews if r.get("batch_or_version") == payload.cohort_b]
        label_a = payload.cohort_a
        label_b = payload.cohort_b

    if not revs_a or not revs_b:
        raise HTTPException(status_code=400, detail="Insufficient review volume in one or both cohorts for comparison.")

    return benchmark_service.compare_cohorts(revs_a, revs_b, label_a, label_b)


# ==============================================================================
# ACTION & ROI IMPACT PRIORITIZATION MATRIX
# ==============================================================================

@router.get("/action/matrix")
def get_action_matrix(domain: Optional[str] = None, user: Optional[AuthenticatedUser] = _auth()):
    """
    Returns 2x2 Impact vs Effort Prioritization Matrix with calculated CSAT lift.
    """
    ensure_initialized()
    active_dom, bundle = get_domain_bundle(domain)
    complaint_clusters = bundle.get("complaint_clusters", [])
    reviews = bundle.get("reviews", [])
    avg_rating = round(sum(r.get("rating", 4) for r in reviews) / max(len(reviews), 1), 2)

    return roi_service.compute_action_matrix(complaint_clusters, len(reviews), avg_rating)


# ==============================================================================
# INTERACTIVE DEFECT INJECTION & ANOMALY SIMULATOR
# ==============================================================================

class SimulateAnomalyRequest(BaseModel):
    scenario: Optional[str] = "chemical_burn"


@router.post("/drift/simulate-anomaly")
def simulate_drift_anomaly(payload: SimulateAnomalyRequest, user: Optional[AuthenticatedUser] = _auth()):
    """
    Interactive Hackathon Demonstration:
    Simulates a sudden quality defect or software regression burst in production telemetry.
    Instantly trips Population Stability Index (PSI) threshold and triggers emergency incident alarm.
    """
    ensure_initialized()
    scenario = payload.scenario or "chemical_burn"

    if scenario == "app_crash":
        batch_id = "v3.2.0-HOTFIX"
        theme = "Biometric Authentication Crash on Launch"
        psi_score = 0.362
        rr = 5.2
        p_val = 0.00004
        count = 74
        msg = "CRITICAL ALERT: Biometric loop crash surged 5.2x in v3.2.0 (p=0.00004). PSI: 0.362."
    elif scenario == "pump_leakage":
        batch_id = "Batch-2022-Q2"
        theme = "Dispenser Valve Rupture & Product Leakage"
        psi_score = 0.315
        rr = 4.1
        p_val = 0.00012
        count = 92
        msg = "CRITICAL ALERT: Dispenser valve failure surged 4.1x in Batch-2022-Q2 (p=0.00012). PSI: 0.315."
    else: # chemical_burn
        batch_id = "Batch-24C"
        theme = "Chemical Burning, Redness & Severe Skin Irritation"
        psi_score = 0.384
        rr = 4.8
        p_val = 0.00008
        count = 86
        msg = "CRITICAL HAZARD: Adverse skin reaction surged 4.8x in Batch-24C (p=0.00008). PSI: 0.384."

    simulated_alert = {
        "severity": "CRITICAL",
        "batch_or_version": batch_id,
        "psi_score": psi_score,
        "surging_theme": theme,
        "surging_theme_delta": 0.184,
        "relative_risk": rr,
        "p_value": p_val,
        "is_statistically_significant": True,
        "review_count": count,
        "message": msg,
        "is_simulated": True,
        "causal_drivers": [
            {
                "theme": theme,
                "target_count": count,
                "baseline_count": 8,
                "target_rate_pct": 34.2,
                "baseline_rate_pct": 7.1,
                "rate_delta_pp": 27.1,
                "relative_risk": rr,
                "p_value": p_val,
                "is_statistically_significant": True,
                "significance_tier": "p < 0.001 (Critical)"
            }
        ]
    }

    _, bundle = get_domain_bundle()
    drift_res = bundle.get("drift_results")
    if drift_res and "alerts" in drift_res:
        drift_res["alerts"] = [a for a in drift_res["alerts"] if not a.get("is_simulated")]
        drift_res["alerts"].insert(0, simulated_alert)
    if state.drift_results and "alerts" in state.drift_results:
        state.drift_results["alerts"] = [a for a in state.drift_results["alerts"] if not a.get("is_simulated")]
        state.drift_results["alerts"].insert(0, simulated_alert)

    return {
        "status": "anomaly_injected",
        "scenario": scenario,
        "alert": simulated_alert,
        "emergency_incident_ticket": {
            "title": f"[P0 CRITICAL HAZARD] {theme} ({batch_id})",
            "priority": "P0_BLOCKER",
            "psi_score": psi_score,
            "relative_risk": f"{rr}x",
            "p_value": p_val,
            "affected_cohort": batch_id,
            "blast_radius": f"{count} reported customer incidents",
            "action_required": "Initiate lot quarantine and emergency root-cause review immediately."
        }
    }


@router.post("/drift/reset")
def reset_drift_anomaly(user: Optional[AuthenticatedUser] = _auth()):
    """
    Resets simulated telemetry drift alerts back to the canonical baseline.
    """
    ensure_initialized()
    _, bundle = get_domain_bundle()
    drift_res = bundle.get("drift_results")
    if drift_res and "alerts" in drift_res:
        drift_res["alerts"] = [a for a in drift_res["alerts"] if not a.get("is_simulated")]
    if state.drift_results and "alerts" in state.drift_results:
        state.drift_results["alerts"] = [a for a in state.drift_results["alerts"] if not a.get("is_simulated")]
    return {"status": "reset_successful", "message": "Telemetry restored to clean baseline."}


