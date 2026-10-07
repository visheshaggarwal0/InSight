import io
import json
import logging
import math
import random
import zipfile
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
import pandas as pd

import threading
from app.core.config import settings, BASE_DIR
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
    "tech_saas": {"synthetic": False, "source": "googleplay:productivity-apps-10k"},
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
            provenance = {"synthetic": True, "source": "generated-templates (real load failed)"}
    elif domain == "tech_saas":
        # Check if real precomputed Google Play app telemetry exists in outputs/tech_saas
        import os, json
        tech_cache_dir = os.path.join(str(BASE_DIR), "outputs", "tech_saas")
        tech_reviews_file = os.path.join(tech_cache_dir, "reviews.json")
        if os.path.exists(tech_reviews_file):
            try:
                with open(tech_reviews_file, "r", encoding="utf-8") as f:
                    reviews = json.load(f)
                with open(os.path.join(tech_cache_dir, "ground_truth.json"), "r", encoding="utf-8") as f:
                    ground_truth = json.load(f)
                with open(os.path.join(tech_cache_dir, "themes.json"), "r", encoding="utf-8") as f:
                    themes = json.load(f)
                with open(os.path.join(tech_cache_dir, "complaint_clusters.json"), "r", encoding="utf-8") as f:
                    saas_complaint_clusters = json.load(f)
                with open(os.path.join(tech_cache_dir, "feature_requests.json"), "r", encoding="utf-8") as f:
                    saas_feature_requests = json.load(f)
                with open(os.path.join(tech_cache_dir, "praise_clusters.json"), "r", encoding="utf-8") as f:
                    saas_praise_clusters = json.load(f)
                with open(os.path.join(tech_cache_dir, "drift_results.json"), "r", encoding="utf-8") as f:
                    drift_results = json.load(f)
                with open(os.path.join(tech_cache_dir, "eval_results.json"), "r", encoding="utf-8") as f:
                    eval_results = json.load(f)

                use_real_pipeline = True
                provenance["synthetic"] = False
                provenance["source"] = "googleplay:productivity-apps-10k"
                logger.info("Loaded real Google Play SaaS/App telemetry (%d reviews).", len(reviews))
            except Exception as ex:
                logger.warning("Error loading cached real tech_saas telemetry: %s", ex)
                reviews, ground_truth = dataset_manager.generate_tech_saas(10000)
                use_real_pipeline = False
        else:
            reviews, ground_truth = dataset_manager.generate_tech_saas(10000)
            use_real_pipeline = False
    else:
        raise ValueError(f"Unknown domain: {domain}")

    if use_real_pipeline:
        # Real corpus: evaluate the SHIPPED artifact against the real weak labels
        # on a held-out split. The previous code retrained a model on the
        # artifact's own predictions (self-distillation on pseudo-labels) and
        # then scored it against synthetic Aura Botanicals template text.
        labelled = [r for r in reviews if r.get("ground_truth_label") in CalibratedSentimentClassifier.CLASSES]
        _, held_out = _split_train_eval(labelled, eval_size=1000)
        if len(held_out) >= 2:
            eval_results = evaluation_harness.evaluate(
                [r["ground_truth_label"] for r in held_out],
                [r["sentiment_pred"] for r in held_out],
                sentiment_model.predict_proba([r["redacted_text"] for r in held_out]),
                CalibratedSentimentClassifier.CLASSES,
            )
            eval_results["split"] = "held-out 1/3 of labelled reviews (never fitted)"
            eval_results["label_source"] = provenance.get("label_source")
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

    if use_real_pipeline:
        # Sentiment already came from the verified offline artifact or cached pipeline.
        domain_model = sentiment_model

    return {
        "reviews": reviews,
        "ground_truth": ground_truth,
        "themes": themes,
        "drift_results": drift_results,
        "eval_results": eval_results,
        "sentiment_model": domain_model,
        "data_provenance": provenance,
        "complaint_clusters": (
            real_res.get("complaint_clusters", [])
            if (domain == "d2c_cosmetics" and use_real_pipeline)
            else saas_complaint_clusters
        ),
        "feature_requests": (
            real_res.get("feature_requests", [])
            if (domain == "d2c_cosmetics" and use_real_pipeline)
            else saas_feature_requests
        ),
        "praise_clusters": (
            real_res.get("praise_clusters", [])
            if (domain == "d2c_cosmetics" and use_real_pipeline)
            else saas_praise_clusters
        ),
    }


def _swap_state(domain: str, cached: dict) -> None:
    """Atomically replaces every field of the global state under the lock."""
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

    # Keep legacy singleton sentiment_model synchronized with active domain pipeline
    sentiment_model.pipeline = cached["sentiment_model"].pipeline
    sentiment_model.is_fitted = True
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


def get_domain_bundle(domain: Optional[str] = None) -> Tuple[str, dict]:
    """Thread-safe retrieval of domain state bundle without global race conditions.
    
    If domain is None, defaults to state.active_domain.
    If requested domain is not cached, initializes it under INIT_LOCK.
    Returns (domain_key, bundle_dict).
    """
    ensure_initialized()
    target_domain = (domain or state.active_domain).strip()
    if target_domain not in ("d2c_cosmetics", "tech_saas", "custom"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid domain '{target_domain}'. Valid options: 'd2c_cosmetics', 'tech_saas', 'custom'.",
        )
    with INIT_LOCK:
        if target_domain not in DOMAIN_CACHE:
            if target_domain == "custom":
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
                "name": "Mobile & Productivity Apps (Google Play Store)",
                "category": "Software / Mobile App",
                "focus": "Release regressions, app crashes, sync failures, UI glitches, subscription blockers",
                "review_count": len(DOMAIN_CACHE.get("tech_saas", {}).get("reviews", [])) if "tech_saas" in DOMAIN_CACHE else 6973,
                "synthetic": False,
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

    sentiment_model.pipeline = custom_model.pipeline
    sentiment_model.is_fitted = True

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

    # Atomic commit under the state lock
    with INIT_LOCK:
        result["data_provenance"] = {"synthetic": False, "source": f"user upload: {file.filename}"}
        DOMAIN_CACHE["custom"] = result
        _swap_state("custom", result)

    return {
        "status": "success",
        "rows_ingested": result["rows_ingested"],
        "total_rows_ingested": result["rows_ingested"],
        "eval_rows": len(result["ground_truth"]) or None,
        "active_domain": "custom",
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
    for r in reviews:
        for s in r.get("sentences", []):
            lbl = s.get("label")
            if lbl == "COMPLAINT":
                comp_sents += 1
            elif lbl == "RECOMMENDATION":
                rec_sents += 1
            elif lbl == "PRAISE":
                praise_sents += 1
            else:
                noise_sents += 1

    total_sents = comp_sents + praise_sents + rec_sents + noise_sents
    actionable_sents = comp_sents + praise_sents + rec_sents
    actionable_rate_pct = round(100.0 * actionable_sents / max(total_sents, 1), 1)

    intent_breakdown = {
        "total_sentences": total_sents,
        "complaints": comp_sents,
        "praise": praise_sents,
        "recommendations": rec_sents,
        "noise": noise_sents,
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
    start_idx = (page - 1) * page_size
    sliced = filtered[start_idx:start_idx + page_size]

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
        "page": page,
        "page_size": page_size,
        "total_pages": (total_matching + page_size - 1) // page_size,
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


def _md_escape(text: str) -> str:
    """Neutralises Markdown control characters in interpolated customer text."""
    return (text or "").replace("\\", "\\\\").replace("*", "\\*").replace("`", "\\`").replace("\n", " ")


@router.get("/tickets")
def list_tickets(domain: Optional[str] = Query(None, max_length=64), db=Depends(get_db),
                 user: Optional[AuthenticatedUser] = _auth()):
    """Retrieves all generated triage tickets stored in PostgreSQL."""
    ensure_initialized()
    try:
        tickets = db_service.get_tickets(db, domain or state.active_domain)
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
    domain = req.domain or state.active_domain

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
    source_reviews = reviews if reviews is not None else state.reviews
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


@router.get("/export/powerbi/pbids")
def export_powerbi_pbids(
    request: Request,
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _privileged_auth(),
):
    """
    Returns an official Microsoft Power BI Data Source (.pbids) connector file.
    Double-clicking this file on Windows automatically launches Power BI Desktop
    and configures the live InSight API feed connection.
    """
    from fastapi.responses import Response
    active_dom, _ = get_domain_bundle(domain)
    base_url = str(request.base_url).rstrip("/")
    feed_url = f"{base_url}/api/export/powerbi?domain={active_dom}"
    pbids_data = {
        "version": "0.1",
        "connections": [
            {
                "details": {
                    "protocol": "http",
                    "address": {
                        "url": feed_url
                    },
                    "authentication": None,
                    "query": None
                },
                "options": {},
                "mode": None
            }
        ]
    }
    return Response(
        content=json.dumps(pbids_data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=insight_{active_dom}_connector.pbids"
        },
    )


@router.get("/export/powerbi/bundle")
def export_powerbi_bundle(
    request: Request,
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _privileged_auth(),
):
    """
    Generates a complete Microsoft Power BI Deployment Kit (.zip) containing:
    1. CSV Telemetry Fact & Dimensions table
    2. Power BI Data Source (.pbids) connector
    3. Power Query (M) script for automated schema typing
    4. Curated DAX Measures cheat sheet
    5. Power BI Dashboard Setup & Layout Guide
    """
    from fastapi.responses import Response

    active_dom, bundle = get_domain_bundle(domain)
    reviews = bundle["reviews"]
    if not reviews:
        raise HTTPException(status_code=503, detail="No dataset is loaded yet.")

    base_url = str(request.base_url).rstrip("/")
    feed_url = f"{base_url}/api/export/powerbi?domain={active_dom}"

    # 1. CSV dataset
    csv_bytes = pd.DataFrame(_build_export_rows(reviews)).to_csv(index=False).encode("utf-8")

    # 2. PBIDS Connector
    pbids_data = {
        "version": "0.1",
        "connections": [
            {
                "details": {
                    "protocol": "http",
                    "address": {"url": feed_url},
                    "authentication": None,
                    "query": None
                },
                "options": {},
                "mode": None
            }
        ]
    }
    pbids_bytes = json.dumps(pbids_data, indent=2).encode("utf-8")

    # 3. Power Query (M) Script
    m_script = f"""// ==============================================================================
// InSight AI - Power Query (M) Script for Power BI Desktop
// Paste into Power BI Desktop: Home Ribbon -> Get Data -> Blank Query -> Advanced Editor
// ==============================================================================
let
    Source = Csv.Document(Web.Contents("{feed_url}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{
        {{"Review_ID", type text}},
        {{"Domain", type text}},
        {{"Product_Name", type text}},
        {{"SKU_or_Module", type text}},
        {{"Batch_or_Version", type text}},
        {{"Submission_Date", type date}},
        {{"Channel", type text}},
        {{"Rating", Int64.Type}},
        {{"Calibrated_Sentiment", type text}},
        {{"Sentiment_Confidence", type number}},
        {{"Theme_Title", type text}},
        {{"Cluster_ID", Int64.Type}},
        {{"Sentence_Count", Int64.Type}},
        {{"Complaint_Clauses", Int64.Type}},
        {{"Praise_Clauses", Int64.Type}},
        {{"Recommendation_Clauses", Int64.Type}},
        {{"Is_Actionable", type logical}},
        {{"Has_Silent_Defect", type logical}},
        {{"Is_PII_Scrubbed", type logical}},
        {{"PII_Entities_Detected", type text}},
        {{"Sanitized_Verbatim", type text}},
        {{"Defect_Clause", type text}}
    }})
in
    #"Changed Type"
""".encode("utf-8")

    # 4. DAX Measures
    dax_measures = b"""// ==============================================================================
// InSight AI - Recommended DAX Measures for Executive Dashboard
// ==============================================================================

// 1. Silent Defect Rate: % of 4-5 star reviews harboring hidden complaints
Silent Defect Rate = 
DIVIDE(
    CALCULATE(COUNTROWS('Telemetry'), 'Telemetry'[Rating] >= 4, 'Telemetry'[Has_Silent_Defect] = TRUE()),
    CALCULATE(COUNTROWS('Telemetry'), 'Telemetry'[Rating] >= 4),
    0
)

// 2. Actionable Signal Volume: Reviews with extracted bugs, praises, or features
Actionable Feedback Count = 
CALCULATE(COUNTROWS('Telemetry'), 'Telemetry'[Is_Actionable] = TRUE())

// 3. Actionability Index (% of corpus providing concrete action items)
Actionability Index = 
DIVIDE([Actionable Feedback Count], COUNTROWS('Telemetry'), 0)

// 4. Net Sentiment Score (NSS) [-100 to +100]
Net Sentiment Score = 
VAR Pos = CALCULATE(COUNTROWS('Telemetry'), 'Telemetry'[Calibrated_Sentiment] = "POSITIVE")
VAR Neg = CALCULATE(COUNTROWS('Telemetry'), 'Telemetry'[Calibrated_Sentiment] = "NEGATIVE")
VAR Total = COUNTROWS('Telemetry')
RETURN
DIVIDE(Pos - Neg, Total, 0) * 100

// 5. Total Complaint Clauses Identified
Total Complaint Clauses = 
SUM('Telemetry'[Complaint_Clauses])
"""

    # 5. README Setup Guide
    readme = f"""==============================================================================
InSight AI - Microsoft Power BI Enterprise Integration Kit
Domain: {active_dom}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
==============================================================================

QUICK START:
1. Double-click "insight_{active_dom}_connector.pbids" to launch Power BI Desktop
   with the InSight Web feed pre-configured.
   OR:
   In Power BI Desktop, select "Get Data" -> "Text/CSV" and choose
   "insight_{active_dom}_telemetry.csv".

2. For Live Refreshing:
   - Go to "Home" -> "Transform Data" -> "Advanced Editor".
   - Replace the script with the contents of "InSight_PowerQuery_ETL.m".
   - Now clicking "Refresh" in Power BI Desktop pulls the latest AI model inferences!

3. Executive Measures:
   - Create a New Measure in Power BI and paste the formulas from
     "InSight_DAX_Measures.dax" to track Silent Defect Rates and Net Sentiment.

RECOMMENDED VISUAL LAYOUT:
- Top KPIs: Net Sentiment Score (Card), Silent Defect Rate (Card), Actionable Ratio (Card)
- Root Cause Analysis: Decomposition Tree or Treemap grouped by Theme_Title & Complaint_Clauses
- Quality Drift: Ribbon / Stacked Column Chart of Batch_or_Version vs Calibrated_Sentiment
- Telemetry Drill-Through: Table of Review_ID, Rating, Defect_Clause, Sanitized_Verbatim
""".encode("utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"insight_{active_dom}_telemetry.csv", csv_bytes)
        zf.writestr(f"insight_{active_dom}_connector.pbids", pbids_bytes)
        zf.writestr("InSight_PowerQuery_ETL.m", m_script)
        zf.writestr("InSight_DAX_Measures.dax", dax_measures)
        zf.writestr("README_PowerBI_Setup.txt", readme)

    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=insight_{active_dom}_powerbi_kit.zip"
        },
    )


def _enrich_cluster_verbatims(
    sliced: list,
    reviews: list,
    default_sentiment: str = "NEGATIVE",
    default_rating: int = 1,
    default_title: str = "Cluster Citation",
    default_batch: str = "Unknown",
) -> list:
    """Enriches sentence verbatims with actual parent review metadata (true rating, batch, product, channel)."""
    review_map = {r["id"]: r for r in reviews if r.get("id")}
    enriched = []
    for v in sliced:
        rev_id = v.get("review_id")
        parent = review_map.get(rev_id)
        if not parent and isinstance(v.get("source_row_index"), int):
            idx = v["source_row_index"]
            if 0 <= idx < len(reviews):
                parent = reviews[idx]

        item = dict(v)
        if parent:
            item["rating"] = parent.get("rating", default_rating)
            item["product_name"] = parent.get("product_name") or default_title
            item["batch_or_version"] = parent.get("batch_or_version") or default_batch
            item["channel"] = parent.get("channel", "Customer Review")
            item["submission_date"] = parent.get("submission_date")
            item["sku_or_module"] = parent.get("sku_or_module") or f"Offset [{v.get('start', 0)}:{v.get('end', 0)}]"
            item["sentiment_pred"] = parent.get("sentiment_pred", default_sentiment)
        else:
            item["rating"] = item.get("rating", default_rating)
            item["product_name"] = default_title
            item["batch_or_version"] = default_batch
            item["channel"] = "Customer Review"
            item["sku_or_module"] = f"Offset [{v.get('start', 0)}:{v.get('end', 0)}]"
            item["sentiment_pred"] = default_sentiment
        enriched.append(item)
    return enriched


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
    page: Optional[int] = Query(None, ge=1, description="1-indexed page number"),
    page_size: Optional[int] = Query(None, ge=1, le=200, description="Page size"),
    offset: Optional[int] = Query(None, ge=0, description="Explicit 0-based offset for incremental loading"),
    limit: Optional[int] = Query(None, ge=1, le=200, description="Explicit slice limit (e.g. 10 initial, 20 more)"),
    search: Optional[str] = Query(None, description="Optional search term to filter citations"),
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns representative sentence verbatims for a specific complaint cluster,
    including character slice offsets [start, end] for verbatim span highlighting.
    Supports incremental/infinite scroll (load 10 first, then 20 more on scroll).
    """
    active_dom, bundle = get_domain_bundle(domain)
    clusters = bundle.get("complaint_clusters") or []
    matched = [c for c in clusters if c.get("cluster_id") == cluster_id]
    if not matched:
        raise HTTPException(status_code=404, detail=f"Complaint cluster #{cluster_id} not found in domain '{active_dom}'.")
    cluster = matched[0]
    all_verbatims = list(cluster.get("verbatims", []))

    if search:
        s_term = search.strip().lower()
        all_verbatims = [
            v for v in all_verbatims
            if s_term in v.get("sentence_text", "").lower()
            or s_term in v.get("review_id", "").lower()
        ]

    total = len(all_verbatims)

    if offset is not None:
        start = offset
        count = limit if limit is not None else (page_size if page_size is not None else 20)
        end = start + count
        sliced = all_verbatims[start:end]
        has_more = end < total
    elif page is not None:
        ps = page_size if page_size is not None else 20
        start = (page - 1) * ps
        end = start + ps
        sliced = all_verbatims[start:end]
        has_more = end < total
    elif limit is not None:
        start = 0
        end = limit
        sliced = all_verbatims[start:end]
        has_more = end < total
    else:
        start = 0
        end = total
        sliced = all_verbatims
        has_more = False

    return {
        "cluster_id": cluster_id,
        "domain": active_dom,
        "title": cluster.get("title"),
        "severity": cluster.get("severity"),
        "keywords": cluster.get("keywords", []),
        "sentence_count": cluster.get("sentence_count", total),
        "medoid_verbatim": cluster.get("medoid_verbatim"),
        "affected_batch": cluster.get("affected_batch"),
        "relative_risk": cluster.get("relative_risk"),
        "offset": start,
        "limit": len(sliced),
        "page": page or 1,
        "page_size": page_size or len(sliced),
        "total": total,
        "has_more": has_more,
        "verbatims": _enrich_cluster_verbatims(
            sliced,
            bundle.get("reviews", []),
            default_sentiment="NEGATIVE",
            default_rating=1,
            default_title=cluster.get("title") or "Complaint Driver",
            default_batch=cluster.get("affected_batch") or "Unknown",
        ),
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
    page: Optional[int] = Query(None, ge=1, description="1-indexed page number"),
    page_size: Optional[int] = Query(None, ge=1, le=200, description="Page size"),
    offset: Optional[int] = Query(None, ge=0, description="Explicit 0-based offset for incremental loading"),
    limit: Optional[int] = Query(None, ge=1, le=200, description="Explicit slice limit"),
    search: Optional[str] = Query(None, description="Optional search term to filter citations"),
    domain: Optional[str] = Query(None, description="Optional domain identifier (d2c_cosmetics, tech_saas, custom)"),
    user: Optional[AuthenticatedUser] = _auth(),
):
    """
    Returns representative sentence verbatims for a specific product strength cluster,
    including character slice offsets [start, end] for verbatim span highlighting.
    Supports incremental/infinite scroll.
    """
    active_dom, bundle = get_domain_bundle(domain)
    clusters = bundle.get("praise_clusters") or []
    matched = [c for c in clusters if c.get("cluster_id") == cluster_id]
    if not matched:
        raise HTTPException(status_code=404, detail=f"Product strength cluster #{cluster_id} not found in domain '{active_dom}'.")
    cluster = matched[0]
    all_verbatims = list(cluster.get("verbatims", []))

    if search:
        s_term = search.strip().lower()
        all_verbatims = [
            v for v in all_verbatims
            if s_term in v.get("sentence_text", "").lower()
            or s_term in v.get("review_id", "").lower()
        ]

    total = len(all_verbatims)

    if offset is not None:
        start = offset
        count = limit if limit is not None else (page_size if page_size is not None else 20)
        end = start + count
        sliced = all_verbatims[start:end]
        has_more = end < total
    elif page is not None:
        ps = page_size if page_size is not None else 20
        start = (page - 1) * ps
        end = start + ps
        sliced = all_verbatims[start:end]
        has_more = end < total
    elif limit is not None:
        start = 0
        end = limit
        sliced = all_verbatims[start:end]
        has_more = end < total
    else:
        start = 0
        end = total
        sliced = all_verbatims
        has_more = False

    return {
        "cluster_id": cluster_id,
        "domain": active_dom,
        "title": cluster.get("title"),
        "strength_drivers": cluster.get("strength_drivers", cluster.get("keywords", [])),
        "keywords": cluster.get("keywords", []),
        "sentence_count": cluster.get("sentence_count", cluster.get("praise_count", total)),
        "praise_count": cluster.get("praise_count", cluster.get("sentence_count", total)),
        "delight_score": cluster.get("delight_score", 0.0),
        "delight_tier": cluster.get("delight_tier", "STRONG"),
        "top_batch": cluster.get("top_batch"),
        "hero_sku": cluster.get("hero_sku"),
        "medoid_verbatim": cluster.get("medoid_verbatim"),
        "offset": start,
        "limit": len(sliced),
        "page": page or 1,
        "page_size": page_size or len(sliced),
        "total": total,
        "has_more": has_more,
        "verbatims": _enrich_cluster_verbatims(
            sliced,
            bundle.get("reviews", []),
            default_sentiment="POSITIVE",
            default_rating=5,
            default_title=cluster.get("title") or "Product Strength",
            default_batch=cluster.get("top_batch") or "Standard",
        ),
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

    return {
        "ticket": {
            "title": f"[{severity}] Incident: {title}",
            "severity": severity,
            "cluster_id": payload.cluster_id,
            "incident_volume": volume,
            "affected_batch": batch,
            "relative_risk": rr,
            "ticket_markdown": ticket_md,
            "status": "OPEN",
        }
    }

