import io
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel
import pandas as pd

from app.core.config import settings
from app.data.datasets import dataset_manager
from app.ml.sentiment import sentiment_model
from app.ml.evaluation import evaluation_harness
from app.ml.clustering import clusterer
from app.ml.drift import drift_detector

router = APIRouter()

# Global in-memory state for active dataset
class AppState:
    def __init__(self):
        self.active_domain: str = "d2c_cosmetics"
        self.reviews: list = []
        self.ground_truth: list = []
        self.themes: list = []
        self.drift_results: dict = {}
        self.eval_results: dict = {}
        self.is_initialized: bool = False

state = AppState()
DOMAIN_CACHE: dict = {}

def compute_domain_artifacts(domain: str) -> dict:
    """Computes and calibrates artifacts for a domain."""
    if domain == "d2c_cosmetics":
        reviews, ground_truth = dataset_manager.generate_d2c_cosmetics(10000)
    elif domain == "tech_saas":
        reviews, ground_truth = dataset_manager.generate_tech_saas(10000)
    else:
        raise ValueError(f"Unknown domain: {domain}")

    # 1. Train & calibrate supervised classifier on a training subset (first 2,000)
    # Strictly disjoint from ground_truth
    train_texts = [r["redacted_text"] for r in reviews[:2000]]
    train_labels = [r["ground_truth_label"] for r in reviews[:2000]]
    sentiment_model.fit(train_texts, train_labels)

    # 2. Run inference across the full corpus
    all_texts = [r["redacted_text"] for r in reviews]
    preds = sentiment_model.predict(all_texts)
    probs = sentiment_model.predict_proba(all_texts)

    for i, r in enumerate(reviews):
        r["sentiment_pred"] = preds[i]
        cls_idx = list(sentiment_model.pipeline.classes_).index(preds[i])
        r["sentiment_confidence"] = round(float(probs[i][cls_idx]), 4)

    # 3. Benchmark model against strictly held-out 1,000 ground truth set
    gt_texts = [r["redacted_text"] for r in ground_truth]
    gt_true = [r["ground_truth_label"] for r in ground_truth]
    gt_preds = sentiment_model.predict(gt_texts)
    gt_probs = sentiment_model.predict_proba(gt_texts)
    eval_results = evaluation_harness.evaluate(
        gt_true, gt_preds, gt_probs, sentiment_model.CLASSES
    )

    # 4. Unsupervised thematic clustering
    cluster_res = clusterer.fit_and_cluster(reviews)
    themes = cluster_res["themes"]
    reviews = cluster_res["reviews"]

    # 5. Temporal & batch drift analysis
    drift_results = drift_detector.analyze_drift(reviews)

    return {
        "reviews": reviews,
        "ground_truth": ground_truth,
        "themes": themes,
        "drift_results": drift_results,
        "eval_results": eval_results
    }

def initialize_domain(domain: str):
    """Initializes and activates domain state using pre-computed cache for instant switching."""
    if domain not in DOMAIN_CACHE:
        DOMAIN_CACHE[domain] = compute_domain_artifacts(domain)

    cached = DOMAIN_CACHE[domain]
    state.active_domain = domain
    state.reviews = cached["reviews"]
    state.ground_truth = cached["ground_truth"]
    state.themes = cached["themes"]
    state.drift_results = cached["drift_results"]
    state.eval_results = cached["eval_results"]
    state.is_initialized = True

# Pre-warm both primary domains on startup for instant zero-latency switching
initialize_domain("d2c_cosmetics")
DOMAIN_CACHE["tech_saas"] = compute_domain_artifacts("tech_saas")

class DomainSelectRequest(BaseModel):
    domain: str

class TicketRequest(BaseModel):
    cluster_id: int

@router.get("/datasets")
def list_datasets():
    return {
        "active_domain": state.active_domain,
        "available_domains": [
            {
                "id": "d2c_cosmetics",
                "name": "D2C Cosmetics & Beauty (Aura Botanicals)",
                "category": "Consumer Goods / Skincare",
                "focus": "Batch lot tracking, formulation changes, skin irritation, packaging defects",
                "review_count": 10000
            },
            {
                "id": "tech_saas",
                "name": "Fintech Mobile App (NovaPay)",
                "category": "Software / Mobile App",
                "focus": "Release regressions, biometric crashes, P2P transfer failures",
                "review_count": 10000
            },
            {
                "id": "custom",
                "name": "Custom Review Dataset (CSV Upload)",
                "category": "User Upload",
                "focus": "On-demand ingestion of any review text and metadata",
                "review_count": len(state.reviews) if state.active_domain == "custom" else 0
            }
        ]
    }

@router.post("/datasets/select")
def select_dataset(req: DomainSelectRequest):
    if req.domain not in ["d2c_cosmetics", "tech_saas"]:
        raise HTTPException(status_code=400, detail="Invalid domain. Choose 'd2c_cosmetics' or 'tech_saas'.")
    initialize_domain(req.domain)
    return {"status": "success", "active_domain": state.active_domain}

@router.post("/datasets/upload")
async def upload_custom_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
    
    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode('utf-8', errors='ignore')))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    try:
        reviews, gt = dataset_manager.parse_custom_csv(df)
        state.reviews = reviews
        state.ground_truth = gt
        state.active_domain = "custom"

        # Fast fit
        train_texts = [r["redacted_text"] for r in state.reviews[:min(2000, len(state.reviews))]]
        train_labels = [r["ground_truth_label"] for r in state.reviews[:min(2000, len(state.reviews))]]
        sentiment_model.fit(train_texts, train_labels)

        all_texts = [r["redacted_text"] for r in state.reviews]
        preds = sentiment_model.predict(all_texts)
        probs = sentiment_model.predict_proba(all_texts)

        for i, r in enumerate(state.reviews):
            r["sentiment_pred"] = preds[i]
            cls_idx = list(sentiment_model.pipeline.classes_).index(preds[i])
            r["sentiment_confidence"] = round(float(probs[i][cls_idx]), 4)

        if len(state.ground_truth) > 0:
            gt_texts = [r["redacted_text"] for r in state.ground_truth]
            gt_true = [r["ground_truth_label"] for r in state.ground_truth]
            gt_preds = sentiment_model.predict(gt_texts)
            gt_probs = sentiment_model.predict_proba(gt_texts)
            state.eval_results = evaluation_harness.evaluate(
                gt_true, gt_preds, gt_probs, sentiment_model.CLASSES
            )

        cluster_res = clusterer.fit_and_cluster(state.reviews)
        state.themes = cluster_res["themes"]
        state.reviews = cluster_res["reviews"]
        state.drift_results = drift_detector.analyze_drift(state.reviews)

        return {"status": "success", "rows_ingested": len(state.reviews), "active_domain": "custom"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error on custom data: {str(e)}")

@router.get("/overview")
def get_overview():
    total = len(state.reviews)
    pos_count = sum(1 for r in state.reviews if r.get("sentiment_pred") == "POSITIVE")
    neu_count = sum(1 for r in state.reviews if r.get("sentiment_pred") == "NEUTRAL")
    neg_count = sum(1 for r in state.reviews if r.get("sentiment_pred") == "NEGATIVE")
    
    pii_count = sum(1 for r in state.reviews if len(r.get("pii_detected", [])) > 0)
    critical_themes = sum(1 for t in state.themes if t.get("severity") == "CRITICAL")

    # 1. Dynamic Rating Distribution (1★ to 5★)
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in state.reviews:
        star = r.get("rating", 3)
        if star in rating_counts:
            rating_counts[star] += 1
            
    star_colors = {1: "#F87171", 2: "#FB923C", 3: "#FBBF24", 4: "#34D399", 5: "#059669"}
    rating_distribution = [
        {
            "star": f"{s}★",
            "count": rating_counts[s],
            "percent": round(rating_counts[s] / total * 100) if total else 0,
            "color": star_colors[s]
        }
        for s in [1, 2, 3, 4, 5]
    ]

    # 2. Dynamic Sentiment by Channel / Source
    channel_map = {}
    for r in state.reviews:
        ch = r.get("channel", "Direct")
        if ch not in channel_map:
            channel_map[ch] = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0, "total": 0}
        sp = r.get("sentiment_pred", "NEUTRAL")
        if sp in channel_map[ch]:
            channel_map[ch][sp] += 1
        channel_map[ch]["total"] += 1

    sentiment_by_source = []
    for ch, stats in channel_map.items():
        ch_total = stats["total"] or 1
        sentiment_by_source.append({
            "label": ch,
            "pos": round(stats["POSITIVE"] / ch_total * 100),
            "neu": round(stats["NEUTRAL"] / ch_total * 100),
            "neg": round(stats["NEGATIVE"] / ch_total * 100)
        })

    # 3. Dynamic Sentiment Trend from Drift Timeline
    sentiment_trend = []
    timeline = state.drift_results.get("timeline", [])
    for b in timeline:
        b_total = b.get("review_count") or 1
        sentiment_trend.append({
            "label": b.get("batch_or_version", "Batch"),
            "pos": round(b.get("positive_count", 0) / b_total * 100),
            "neu": round(b.get("neutral_count", 0) / b_total * 100),
            "neg": round(b.get("negative_count", 0) / b_total * 100)
        })

    if not sentiment_trend:
        pos_rate = round(pos_count / total * 100) if total else 0
        neu_rate = round(neu_count / total * 100) if total else 0
        neg_rate = round(neg_count / total * 100) if total else 0
        sentiment_trend = [{"label": "Batch Current", "pos": pos_rate, "neu": neu_rate, "neg": neg_rate}]

    # 4. Dynamic Keyword Cloud extracted from thematic clusters
    cloud_keywords = []
    seen = set()
    palette = [
        ("#EF4444", "2.0rem", 800),
        ("#DC2626", "1.5rem", 700),
        ("#0F382E", "2.2rem", 800),
        ("#059669", "1.6rem", 700),
        ("#10B981", "1.4rem", 600),
        ("#D97706", "1.3rem", 700),
        ("#334155", "1.2rem", 600),
        ("#475569", "1.1rem", 500),
        ("#6EE7B7", "1.0rem", 600),
        ("#94A3B8", "0.9rem", 500)
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
                    "count": t.get("review_count", 100)
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
            "percent": f"+{int(top_alert['psi_score'] * 100)}%",
            "period": f"in {top_alert['batch_or_version']}",
            "isWarning": True,
            "psiAlert": f"PSI {round(top_alert['psi_score'], 2)}"
        })

    critical_themes_list = [t for t in state.themes if t.get("severity") in ["CRITICAL", "HIGH"]]
    if critical_themes_list:
        top_crit = critical_themes_list[0]
        recent_insights.append({
            "title": f"Surge in '{top_crit['title']}' ({top_crit['negative_rate']}% negative)",
            "percent": f"{top_crit['review_count']} reviews",
            "period": "active defect cluster",
            "isWarning": True,
            "psiAlert": None
        })

    pos_rate_val = round(pos_count / total * 100) if total else 0
    recent_insights.append({
        "title": f"Overall product satisfaction at {pos_rate_val}% positive sentiment",
        "percent": f"{pos_rate_val}%",
        "period": "across all channels",
        "isWarning": False,
        "psiAlert": None
    })

    return {
        "domain": state.active_domain,
        "total_reviews": total,
        "sentiment_counts": {
            "POSITIVE": pos_count,
            "NEUTRAL": neu_count,
            "NEGATIVE": neg_count
        },
        "positive_rate": round((pos_count / total * 100), 1) if total else 0,
        "negative_rate": round((neg_count / total * 100), 1) if total else 0,
        "pii_redacted_count": pii_count,
        "pii_redacted_rate": round((pii_count / total * 100), 1) if total else 0,
        "critical_themes_count": critical_themes,
        "active_alerts": len(state.drift_results.get("alerts", [])),
        "rating_distribution": rating_distribution,
        "sentiment_by_source": sentiment_by_source,
        "sentiment_trend": sentiment_trend,
        "keyword_cloud": cloud_keywords,
        "recent_insights": recent_insights
    }

@router.get("/themes")
def get_themes():
    return {
        "themes": state.themes,
        "total_themes": len(state.themes)
    }

@router.get("/verbatims")
def get_verbatims(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sentiment: Optional[str] = Query(None),
    cluster_id: Optional[int] = Query(None),
    batch: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    show_raw_pii: bool = Query(False)
):
    filtered = state.reviews

    if sentiment:
        filtered = [r for r in filtered if r.get("sentiment_pred") == sentiment.upper()]
    if cluster_id is not None:
        filtered = [r for r in filtered if r.get("cluster_id") == cluster_id]
    if batch:
        filtered = [r for r in filtered if r.get("batch_or_version") == batch]
    if search:
        s_lower = search.lower()
        filtered = [r for r in filtered if s_lower in r.get("redacted_text", "").lower()]

    total_matching = len(filtered)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    sliced = filtered[start_idx:end_idx]

    # Map text display based on role-based PII switch
    results = []
    for r in sliced:
        item = dict(r)
        item["display_text"] = r["raw_text"] if show_raw_pii else r["redacted_text"]
        results.append(item)

    return {
        "total": total_matching,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_matching + page_size - 1) // page_size,
        "verbatims": results
    }

@router.get("/drift")
def get_drift():
    return state.drift_results

@router.get("/governance")
def get_model_governance():
    return {
        "model_architecture": "Calibrated Logistic Regression (Platt Scaling) over Sublinear N-Gram TF-IDF",
        "evaluation": state.eval_results
    }

@router.post("/ticket/generate")
def generate_ticket(req: TicketRequest):
    # Find matching theme
    theme = next((t for t in state.themes if t["cluster_id"] == req.cluster_id), None)
    if not theme:
        raise HTTPException(status_code=404, detail="Cluster ID not found.")

    # Grab top 5 verbatims
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

    batches = list(set(r.get("batch_or_version", "N/A") for r in theme_reviews))
    quotes = "\n".join([f"- \"{r['redacted_text']}\" (ID: {r['id']}, Rating: {r['rating']}★, {r.get('batch_or_version')})" for r in theme_reviews])

    markdown = f"""### {ticket_type}
**Title:** {title}  
**Severity:** {theme['severity']}  
**{affected_field}:** {", ".join(batches)}  
**Incident Volume:** {theme['review_count']} user complaints ({theme['negative_rate']}% negative)  
**Core Keywords:** {", ".join(theme['keywords'])}  

#### Observed Customer Verbatims (Masked):
{quotes}

#### Recommended Action Items:
1. Halt distribution / trigger hotfix rollback for affected release or batch.
2. Cross-reference quality control logs and packaging vendor batch specs.
3. Validate automated unit tests and customer support response scripts.
"""
    return {
        "cluster_id": req.cluster_id,
        "title": title,
        "severity": theme['severity'],
        "ticket_markdown": markdown
    }

@router.get("/export/csv")
@router.get("/export/powerbi")
def export_powerbi_telemetry():
    """
    Streams clean, tabular telemetry directly for Microsoft Power BI Web Connector, Excel, or CSV download.
    Contains pre-calculated sentiment, confidence, PII status, and cluster assignments.
    """
    from fastapi.responses import Response

    df_rows = []
    for r in state.reviews:
        df_rows.append({
            "Review_ID": r.get("id"),
            "Domain": r.get("domain"),
            "Product_Name": r.get("product_name"),
            "SKU_or_Module": r.get("sku_or_module"),
            "Batch_or_Version": r.get("batch_or_version"),
            "Channel": r.get("channel"),
            "Rating": r.get("rating"),
            "Calibrated_Sentiment": r.get("sentiment_pred"),
            "Sentiment_Confidence": r.get("sentiment_confidence"),
            "Theme_Title": r.get("theme_title", "General"),
            "Cluster_ID": r.get("cluster_id"),
            "Is_PII_Scrubbed": len(r.get("pii_detected", [])) > 0,
            "PII_Entities_Detected": ";".join(r.get("pii_detected", [])),
            "Sanitized_Verbatim": r.get("redacted_text"),
            "Defect_Clause": r.get("highlight_span", {}).get("text", "") if r.get("highlight_span") else ""
        })
    export_df = pd.DataFrame(df_rows)
    csv_str = export_df.to_csv(index=False)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=insight_{state.active_domain}_telemetry.csv",
            "Access-Control-Allow-Origin": "*"
        }
    )

