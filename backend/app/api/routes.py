import io
import logging
import random
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
import pandas as pd

import threading
from app.core.config import settings
from app.core.database import get_db
from app.data.datasets import dataset_manager
from app.data.real_loader import real_data_loader
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

    if use_real_pipeline:
        # Sentiment already came from the verified offline artifact.
        domain_model = sentiment_model

    return {
        "reviews": reviews,
        "ground_truth": ground_truth,
        "themes": themes,
        "drift_results": drift_results,
        "eval_results": eval_results,
        "sentiment_model": domain_model,
        "data_provenance": provenance,
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


class DomainSelectRequest(BaseModel):
    domain: str


class TicketRequest(BaseModel):
    cluster_id: int


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
                "review_count": len(state.reviews) if state.active_domain == "d2c_cosmetics" else 10000,
                "synthetic": False,
            },
            {
                "id": "tech_saas",
                "name": "Fintech Mobile App (NovaPay)",
                "category": "Software / Mobile App",
                "focus": "Release regressions, biometric crashes, P2P transfer failures",
                "review_count": len(state.reviews) if state.active_domain == "tech_saas" else 10000,
                "synthetic": True,
            },
            {
                "id": "custom",
                "name": "Custom Review Dataset (CSV Upload)",
                "category": "User Upload",
                "focus": "On-demand ingestion of any review text and metadata",
                "review_count": len(state.reviews) if state.active_domain == "custom" else 0,
                "synthetic": None,
            },
        ],
    }


@router.post("/datasets/select")
def select_dataset(req: DomainSelectRequest, user: Optional[AuthenticatedUser] = _auth()):
    if req.domain not in ("d2c_cosmetics", "tech_saas"):
        raise HTTPException(
            status_code=400,
            detail="Invalid domain. Choose 'd2c_cosmetics' or 'tech_saas'. Use the upload control to load a custom CSV.",
        )
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
async def upload_custom_csv(
    file: UploadFile = File(...),
    user: Optional[AuthenticatedUser] = _privileged_auth(),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Stream with a hard byte ceiling instead of `await file.read()`, which
    # buffered an unbounded body into memory.
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

    try:
        result = await run_in_threadpool(_process_custom_csv, b"".join(chunks), file.filename)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Pipeline failed on custom upload %s", file.filename)
        raise HTTPException(status_code=500, detail="The analysis pipeline failed on this dataset.")

    # Atomic commit: every field swaps together under the lock, and
    # is_initialized is set so the lazy initializer cannot clobber the upload
    # on the next read (which previously discarded it entirely).
    with INIT_LOCK:
        state.active_domain = "custom"
        _swap_state("custom", result)

    return {
        "status": "success",
        "rows_ingested": len(state.reviews),
        "total_rows_ingested": result["total_rows"],
        "eval_rows": len(result["ground_truth"]) or None,
        "active_domain": "custom",
        "data_provenance": result["data_provenance"],
    }


@router.get("/overview")
def get_overview(user: Optional[AuthenticatedUser] = _auth()):
    ensure_initialized()
    total = len(state.reviews)
    pos_count = sum(1 for r in state.reviews if r.get("sentiment_pred") == "POSITIVE")
    neu_count = sum(1 for r in state.reviews if r.get("sentiment_pred") == "NEUTRAL")
    neg_count = sum(1 for r in state.reviews if r.get("sentiment_pred") == "NEGATIVE")

    pii_count = sum(1 for r in state.reviews if len(r.get("pii_detected") or []) > 0)
    critical_themes = sum(1 for t in state.themes if t.get("severity") == "CRITICAL")

    # 1. Dynamic Rating Distribution (1 to 5 stars)
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in state.reviews:
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
    for r in state.reviews:
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
    for b in state.drift_results.get("timeline", []):
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
    for t in state.themes:
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
    alerts = state.drift_results.get("alerts", [])
    recent_insights = []
    if alerts:
        top_alert = alerts[0]
        recent_insights.append({
            "title": top_alert["message"],
            # PSI is a unitless divergence index. Rendering it as "+25%"
            # implied a 25% increase in something and is semantically wrong.
            "metric": {"value": f"{top_alert['psi_score']:.2f}", "kind": "index"},
            "metric_label": "PSI",
            "period": f"in {top_alert['batch_or_version']}",
            "isWarning": True,
            "psiAlert": f"PSI {top_alert['psi_score']:.2f}",
        })

    critical_themes_list = [t for t in state.themes if t.get("severity") in ("CRITICAL", "HIGH")]
    if critical_themes_list:
        top_crit = critical_themes_list[0]
        recent_insights.append({
            "title": f"Highest-severity cluster '{top_crit['title']}' ({top_crit['negative_rate']}% negative)",
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

    return {
        "domain": state.active_domain,
        "data_provenance": state.data_provenance,
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
    }


@router.get("/themes")
def get_themes(user: Optional[AuthenticatedUser] = _auth()):
    ensure_initialized()
    return {
        "themes": state.themes,
        "total_themes": len(state.themes),
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
    user: Optional[AuthenticatedUser] = _auth(),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sentiment: Optional[str] = Query(None, max_length=16),
    cluster_id: Optional[int] = Query(None),
    batch: Optional[str] = Query(None, max_length=64),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
    show_raw_pii: bool = Query(False),
):
    ensure_initialized()

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
                role, state.active_domain, page,
            )
    if show_raw_pii and not unmask_allowed:
        raise HTTPException(
            status_code=403,
            detail="Unredacted customer text requires an authorised compliance role.",
        )

    # Copy: `state.reviews` is a reference, and any future in-place filter
    # would corrupt global state.
    filtered = list(state.reviews)

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
        "pii_masked": not unmask_allowed,
        "verbatims": results,
    }


@router.get("/drift")
def get_drift(user: Optional[AuthenticatedUser] = _auth()):
    ensure_initialized()
    return state.drift_results


@router.get("/governance")
def get_model_governance(user: Optional[AuthenticatedUser] = _auth()):
    ensure_initialized()
    return {
        "model_architecture": "Calibrated Logistic Regression (Platt Scaling) over Sublinear N-Gram TF-IDF",
        "evaluation": state.eval_results,
        "data_provenance": state.data_provenance,
        "severity_thresholds": severity_snapshot(),
        "auth_required": settings.REQUIRE_AUTH,
    }


@router.post("/ticket/generate")
def generate_ticket(req: TicketRequest, db=Depends(get_db),
                    user: Optional[AuthenticatedUser] = _auth()):
    ensure_initialized()
    theme = next((t for t in state.themes if t["cluster_id"] == req.cluster_id), None)
    if not theme:
        raise HTTPException(status_code=404, detail="Cluster ID not found.")

    theme_reviews = [r for r in state.reviews if r.get("cluster_id") == req.cluster_id][:5]

    is_d2c = (state.active_domain == "d2c_cosmetics")

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
**Incident Volume:** {theme['review_count']} user complaints ({theme['negative_rate']}% negative)
**Core Keywords:** {", ".join(theme.get("keywords", []))}
**Data Source:** {"synthetic (generated templates)" if state.data_provenance.get("synthetic") else "real customer telemetry"}

#### Observed Customer Verbatims (Masked):
{quotes}

#### Recommended Action Items:
1. Halt distribution / trigger hotfix rollback for affected release or batch.
2. Cross-reference quality control logs and packaging vendor batch specs.
3. Validate automated unit tests and customer support response scripts.
"""

    # Session lifecycle is owned by Depends(get_db); the previous manual
    # SessionLocal()/close() pair leaked connections whenever the write raised.
    ticket_id = None
    try:
        ticket_record = db_service.save_ticket(
            db=db,
            domain_id=state.active_domain,
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


def _build_export_rows() -> list:
    """Redacted-only telemetry export. raw_text is never included."""
    return [
        {
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
            "Is_PII_Scrubbed": bool(r.get("pii_detected")),
            "PII_Entities_Detected": ";".join(sorted(r.get("pii_detected") or [])),
            "Sanitized_Verbatim": r.get("redacted_text"),
            "Defect_Clause": (r.get("highlight_span") or {}).get("text", ""),
        }
        for r in state.reviews
    ]


@router.get("/export/powerbi")
@router.get("/export/csv", include_in_schema=False)
def export_powerbi_telemetry(user: Optional[AuthenticatedUser] = _privileged_auth()):
    """
    Streams clean, tabular telemetry for Microsoft Power BI Web Connector, Excel
    or CSV download. Contains redacted verbatim text only.

    Restricted to authorised roles because it returns the entire corpus.
    """
    from fastapi.responses import Response

    ensure_initialized()

    if not state.reviews:
        raise HTTPException(status_code=503, detail="No dataset is loaded yet.")

    csv_str = pd.DataFrame(_build_export_rows()).to_csv(index=False)
    # No hand-written Access-Control-Allow-Origin: a wildcard here made the
    # full corpus fetchable by any origin on the internet, on top of the
    # credentialed CORSMiddleware configuration.
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=insight_{state.active_domain}_telemetry.csv"
        },
    )
