"""complaint_clustering.py
Complaint-only MiniLM embedding + MiniBatchKMeans clustering + c-TF-IDF.

This module operates exclusively on the COMPLAINT sentence pool produced
by sentence_pipeline.classify_and_route_corpus().  It is the "Complaint
Cluster Dashboard" branch of the new architecture.

Relationship to existing code
-------------------------------
* Reuses the same MiniLM model (all-MiniLM-L6-v2) already used by
  theme_inference.py and backend/app/ml/clustering.py.
* Does NOT replace review-level theme clustering.  The existing six review
  themes (Eye Care, Moisturizers, Acne, etc.) remain intact in run_pipeline.
* Adds a NEW complaint-specific cluster dimension that operates on sentences,
  not full reviews.

Design
------
* Lazy singleton: the SentenceTransformer is loaded once, not at import.
* The number of complaint clusters (n_clusters) auto-scales to
  max(2, min(configured_k, n_complaint_sentences // 5)).
* Verbatim span highlighting: every cluster output includes the original
  sentence_id, review_id, source_row_index, and character offsets so the
  dashboard can highlight the exact sentence in the original review.

PROVISIONAL NOTICES:
  - Cluster labels are unsupervised and not human-annotated.
  - Cluster titles are DERIVED from the same member sentences that define the
    cluster, so a title restates the cluster definition. It is descriptive,
    never causal, and never LLM-generated.
  - c-TF-IDF keywords are distinctive within the complaint corpus (they are
    class-based TF-IDF terms, not validated root causes).
  - Cluster count is heuristic; optimal k requires human evaluation.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import importlib.util
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

from app.ml.sentence_pipeline import SentenceRecord
from app.ml.pipeline_config import COMPLAINT_CLUSTERING, HDBSCAN_CONFIG, CLUSTERING_MODE, embedding_cache_key

HDBSCAN_AVAILABLE: bool = (
    importlib.util.find_spec("hdbscan") is not None
    and importlib.util.find_spec("umap") is not None
)

try:
    from app.ml.severity import classify_complaint_severity
except ImportError:  # pragma: no cover - only if app.ml is not importable
    # Single source of truth is app.ml.severity. This fallback exists only so a
    # broken/mis-installed backend cannot make the whole ml package unimportable;
    # it reads the SAME thresholds from pipeline_config.
    _SEV = COMPLAINT_CLUSTERING["severity_thresholds"]

    def classify_complaint_severity(count: int, total_complaints: int = 0) -> str:
        if total_complaints and total_complaints > 0:
            share = count / total_complaints
            if share >= 0.20 and count >= 3:
                return "CRITICAL"
            if share >= 0.14 and count >= 2:
                return "HIGH"
            if share >= 0.08:
                return "MEDIUM"
            return "LOW"
        if count >= _SEV["critical"]:
            return "CRITICAL"
        if count >= _SEV["high"]:
            return "HIGH"
        if count >= _SEV["medium"]:
            return "MEDIUM"
        return "LOW"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# All values are read live from pipeline_config.COMPLAINT_CLUSTERING so that a
# threshold is changed in exactly one place.

_MODEL_NAME: str = COMPLAINT_CLUSTERING["model_name"]
_DEFAULT_N_CLUSTERS: int = COMPLAINT_CLUSTERING["n_clusters"]
_EMBEDDING_DIM: int = 384
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CACHE_DIR = _PROJECT_ROOT / "outputs" / "complaint_cluster_cache"


# ---------------------------------------------------------------------------
# Lazy MiniLM encoder singleton (same model as theme_inference.py)
# ---------------------------------------------------------------------------

_ENCODER = None


def _get_encoder():
    """Load the SentenceTransformer model once (lazy singleton)."""
    global _ENCODER
    if _ENCODER is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer '%s' for complaint clustering …", _MODEL_NAME)
        t0 = time.time()
        try:
            _ENCODER = SentenceTransformer(_MODEL_NAME)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load SentenceTransformer '{_MODEL_NAME}' for complaint clustering. "
                f"If you are working offline, ensure the model has been downloaded once with an internet connection, "
                f"or run 'python scripts/download_models.py'. Original error: {exc}"
            ) from exc
        logger.info("  Model loaded in %.2fs", time.time() - t0)
    return _ENCODER


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------

def embed_sentences(texts: List[str], cache_key_suffix: str = "") -> np.ndarray:
    """Encode texts using MiniLM, with disk caching.

    Returns:
        Float32 array of shape (N, 384), L2-normalized.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Content-addressable cache key. This MUST cover the full ordered text of
    # every row plus the encoder identity: a key built from the first/last few
    # sentences and the corpus length collided whenever the middle of the pool
    # changed (i.e. exactly when the complaint heuristics are edited), returning
    # a stale matrix computed against a DIFFERENT sentence list.
    cache_key = embedding_cache_key(
        texts,
        model_name=_MODEL_NAME,
        dim=_EMBEDDING_DIM,
        salt=cache_key_suffix,
    )
    cache_file = _CACHE_DIR / f"emb_{cache_key}.npy"

    if cache_file.exists():
        logger.debug("Embedding cache hit: %s", cache_file.name)
        return np.load(cache_file)

    encoder = _get_encoder()
    t0 = time.time()
    embeddings = encoder.encode(
        texts,
        batch_size=COMPLAINT_CLUSTERING["batch_size"],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    logger.info("  Encoded %d sentences in %.2fs", len(texts), time.time() - t0)

    try:
        np.save(cache_file, embeddings)
    except Exception as exc:
        logger.warning("Could not write embedding cache: %s", exc)

    return embeddings


# ---------------------------------------------------------------------------
# Generic review and cosmetics filler tokens that overshadow specific defect terminology
# ---------------------------------------------------------------------------

_VOC_STOPWORDS = {
    "product", "products", "use", "used", "using", "really", "feel", "feels", "feeling",
    "tried", "bought", "got", "just", "like", "time", "day", "days", "face",
    "skin", "make", "makes", "think", "love", "way", "bit", "lot", "good",
    "great", "cream", "eyes", "eye", "moisturizer", "cleanser", "serum",
    "oil", "lotion", "apply", "applying", "applied", "didn", "don", "wasn",
    "wouldn", "couldn", "ve", "ll", "went", "come", "came", "going", "know",
    "item", "brand", "order", "ordered", "purchase", "purchased", "bottle"
}
_COMBINED_STOPWORDS = list(ENGLISH_STOP_WORDS.union(_VOC_STOPWORDS))


# ---------------------------------------------------------------------------
# c-TF-IDF keyword extraction
# ---------------------------------------------------------------------------

def extract_ctfidf_keywords(
    cluster_texts: Dict[int, List[str]],
    top_n: int = 8,
) -> Dict[int, List[str]]:
    """Compute class-based c-TF-IDF keywords for each complaint cluster.

    Implements class-based TF-IDF (Cohan, 2005) where each CLUSTER is a
    "class" and each sentence inside it is a document:

        tf_c(t, c) = 1 + log(t_c(t))
        idf(t)     = log(1 + A / f(t))
        weight_c(t) = tf_c(t, c) * idf(t)

    where t_c(t) is the count of t across cluster c's documents, f(t) is the
    number of clusters in which t appears, and A is the average of f(t) over
    the observed terms. Terms that appear in every cluster get the smallest
    weight; terms concentrated in one cluster dominate that cluster's ranking.

    This is NOT plain TF-IDF. The previous implementation ran a TfidfVectorizer
    over the k concatenated cluster documents, which L2-normalised each cluster
    document independently, so a 3-sentence cluster outranked a 300-sentence
    cluster, and with ``min_df=1`` every hapax received full IDF weight.

    Args:
        cluster_texts: {cluster_id: [list of sentence texts in this cluster]}
        top_n: Maximum number of keywords to return per cluster.

    Returns:
        {cluster_id: [keyword, ...]} — strictly positive scores only, sorted by
        descending c-TF-IDF weight. A cluster whose entire vocabulary is
        stop-worded away maps to an empty list rather than a padded one.
    """
    cluster_ids = sorted(cluster_texts.keys())
    docs = [" ".join(cluster_texts[c]) for c in cluster_ids]

    if not any(d.strip() for d in docs) or top_n <= 0:
        return {c: [] for c in cluster_ids}

    def _count(stop_words) -> Optional[Tuple[Any, np.ndarray]]:
        """CountVectorizer is used purely as a tokenizer/counter here.

        Weighting is done explicitly below so the c-TF-IDF formula is visible
        in this file rather than hidden inside sklearn's TF-IDF pipeline.
        """
        try:
            vec = CountVectorizer(
                max_features=3000,
                ngram_range=(1, 2),
                stop_words=stop_words,
                min_df=1,
            )
            return vec.fit_transform(docs), vec.get_feature_names_out()
        except ValueError:
            return None

    counted = _count(_COMBINED_STOPWORDS)
    if counted is None:
        # Fall back to standard english stop words if domain filtering
        # eliminated every term.
        counted = _count("english")
    if counted is None:
        logger.warning("c-TF-IDF: no usable terms in cluster vocabulary.")
        return {c: [] for c in cluster_ids}

    counts, feature_names = counted
    counts = np.asarray(counts.todense(), dtype=np.float64)  # (n_classes, n_terms)

    # f(t): number of classes (clusters) in which term t appears at least once.
    per_class_presence = (counts > 0).astype(np.float64)
    f_t = per_class_presence.sum(axis=0)                      # (n_terms,)

    observed = f_t > 0
    if not observed.any():
        return {c: [] for c in cluster_ids}

    # A = average number of classes per observed term (Cohan/Chindock).
    A = float(f_t[observed].mean())
    if A <= 0:
        return {c: [] for c in cluster_ids}

    # idf(t) = log(1 + A / f(t)); only defined for observed terms. Unobserved
    # terms (f(t) == 0) would divide by zero and are excluded by the mask.
    idf = np.zeros_like(f_t)
    idf[observed] = np.log(1.0 + A / f_t[observed])

    keywords: Dict[int, List[str]] = {}
    for doc_idx, c_id in enumerate(cluster_ids):
        term_counts = counts[doc_idx]
        positive = term_counts > 0
        if not positive.any():
            keywords[c_id] = []
            continue

        tf = np.zeros_like(term_counts)
        tf[positive] = 1.0 + np.log(term_counts[positive])
        weights = tf * idf

        # Restrict the ranking to terms this cluster actually contains. Every
        # other entry has a weight of exactly 0.0; including them is how the
        # previous version fabricated keywords such as "unfortunately" for a
        # cluster with only three in-vocabulary terms.
        candidates = np.flatnonzero(positive)
        order = candidates[np.argsort(weights[candidates])[::-1]][:top_n]
        keywords[c_id] = feature_names[order].tolist()

    return keywords



# ---------------------------------------------------------------------------
# Main clustering function
# ---------------------------------------------------------------------------

def _compute_relative_risk(
    sents: List[SentenceRecord],
    review_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute empirical relative risk (causal attribution) across batches/versions.

    Identifies which batch or SKU has an over-indexed complaint concentration.
    RR = P(Defect | Batch) / P(Defect | Other Batches).
    """
    if not review_metadata:
        return {"affected_batch": None, "relative_risk": 1.0, "is_statistically_significant": False}

    batch_counts: Dict[str, int] = {}
    for s in sents:
        meta = review_metadata.get(s.review_id, {})
        batch = meta.get("batch_or_version") or "General"
        batch_counts[batch] = batch_counts.get(batch, 0) + 1

    if not batch_counts:
        return {"affected_batch": None, "relative_risk": 1.0, "is_statistically_significant": False}

    # Find highest volume batch in this cluster
    top_batch, cluster_batch_count = max(batch_counts.items(), key=lambda x: x[1])
    
    # Calculate baseline representation across corpus
    total_cluster_sents = len(sents)
    total_corpus_for_batch = sum(
        1 for r_id, meta in review_metadata.items() if (meta.get("batch_or_version") or "General") == top_batch
    )
    total_corpus = max(len(review_metadata), 1)

    p_cluster_in_batch = cluster_batch_count / max(total_corpus_for_batch, 1)
    other_batch_cluster_count = total_cluster_sents - cluster_batch_count
    other_corpus_count = max(total_corpus - total_corpus_for_batch, 1)
    p_cluster_in_other = other_batch_cluster_count / other_corpus_count

    rr = round(p_cluster_in_batch / max(p_cluster_in_other, 1e-4), 2)
    # Simple significance heuristic: at least 5 instances and RR >= 1.5
    is_sig = bool(cluster_batch_count >= 5 and rr >= 1.5)

    return {
        "affected_batch": top_batch if is_sig else (top_batch if cluster_batch_count >= 3 else "Omnichannel"),
        "relative_risk": rr if is_sig else 1.0,
        "is_statistically_significant": is_sig,
        "batch_count": cluster_batch_count,
    }


def cluster_complaint_sentences(
    complaint_sentences: List[SentenceRecord],
    n_clusters: int = _DEFAULT_N_CLUSTERS,
    random_state: int = 42,
    mode: str = "kmeans",
    review_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Embed, cluster, and summarize complaint sentences using KMeans or HDBSCAN.

    Args:
        complaint_sentences: Sentences from the COMPLAINT pool.
        n_clusters: Desired number of root-cause clusters (auto-scaled down if corpus is small).
        random_state: For reproducibility.
        mode: "kmeans" (default) or "hdbscan" (density-based with outlier radar).
        review_metadata: Optional map of {review_id: {batch_or_version, sku_or_module}} for Relative Risk.

    Returns:
        A dict with clusters, medoids, c-TF-IDF keywords, and outlier pools.
    """
    n = len(complaint_sentences)

    if n == 0:
        logger.warning("Complaint clustering: no sentences in pool — skipping.")
        return {
            "clusters": [],
            "n_complaint_sentences": 0,
            "n_clusters_actual": 0,
            "is_provisional": True,
            "provisional_notices": ["No complaint sentences found in corpus."],
        }

    k = max(1, min(n_clusters, max(1, n // 5), n))
    texts = [s.sentence_text for s in complaint_sentences]

    # Step 1: MiniLM embeddings (384-d, L2-normalized)
    logger.info("Complaint clustering: embedding %d complaint sentences …", n)
    embeddings = embed_sentences(texts, cache_key_suffix=f"_k{k}")

    # Step 2: Clustering (KMeans or HDBSCAN)
    labels = None
    kmeans_obj = None
    if mode == "hdbscan" and HDBSCAN_AVAILABLE:
        try:
            import umap  # type: ignore[import]
            import hdbscan as hdbscan_lib  # type: ignore[import]

            logger.info("Complaint clustering: running UMAP + HDBSCAN …")
            reducer = umap.UMAP(
                n_components=min(10, n - 2) if n > 3 else 2,
                metric="cosine",
                n_neighbors=min(15, n - 1),
                random_state=random_state,
            )
            X_reduced = reducer.fit_transform(embeddings)
            clusterer = hdbscan_lib.HDBSCAN(
                min_cluster_size=max(3, min(10, n // 10)),
                min_samples=max(2, min(5, n // 20)),
                cluster_selection_method="eom",
            )
            labels = clusterer.fit_predict(X_reduced)
            logger.info("HDBSCAN complaint clusters: %d clusters, %d noise", len(set(labels) - {-1}), int((labels == -1).sum()))
        except Exception as exc:
            logger.warning("HDBSCAN failed (%s); falling back to MiniBatchKMeans.", exc)
            labels = None

    if labels is None:
        logger.info("Complaint clustering: fitting MiniBatchKMeans(k=%d) …", k)
        kmeans = MiniBatchKMeans(
            n_clusters=k,
            random_state=random_state,
            batch_size=min(COMPLAINT_CLUSTERING["batch_size"], n),
            n_init=COMPLAINT_CLUSTERING["n_init"],
        )
        labels = kmeans.fit_predict(embeddings)
        kmeans_obj = kmeans

    # Step 3: Group sentences by cluster
    unique_cids = sorted(list(set(labels)))
    cluster_sentence_map: Dict[int, List[SentenceRecord]] = {c: [] for c in unique_cids}
    for sent, cid in zip(complaint_sentences, labels):
        cluster_sentence_map[int(cid)].append(sent)

    # Step 4: c-TF-IDF keywords across regular clusters (excluding noise -1)
    regular_cids = [c for c in unique_cids if c >= 0]
    cluster_texts_map = {c: [s.sentence_text for s in cluster_sentence_map[c]] for c in regular_cids}
    keywords_map = extract_ctfidf_keywords(
        cluster_texts_map, top_n=COMPLAINT_CLUSTERING["top_keywords"],
    )

    # Step 5: Build cluster summaries
    n_verbatims = COMPLAINT_CLUSTERING["n_verbatims"]
    clusters = []

    for cid in unique_cids:
        sents = cluster_sentence_map[cid]
        count = len(sents)
        if count == 0:
            continue

        cluster_indices = [i for i, lbl in enumerate(labels) if lbl == cid]
        c_embs = embeddings[cluster_indices]

        # Medoid calculation
        if kmeans_obj is not None and cid >= 0:
            centroid = kmeans_obj.cluster_centers_[cid]
            dists = np.linalg.norm(c_embs - centroid, axis=1)
            medoid_sent = complaint_sentences[cluster_indices[int(np.argmin(dists))]]
        else:
            # Cosine mean medoid
            mean_vec = c_embs.mean(axis=0, keepdims=True)
            dists = np.linalg.norm(c_embs - mean_vec, axis=1)
            medoid_sent = complaint_sentences[cluster_indices[int(np.argmin(dists))]]

        ordered_sents = [medoid_sent] + [s for s in sents if s.sentence_id != medoid_sent.sentence_id]
        verbatims = [
            {
                "sentence_id": s.sentence_id,
                "review_id": s.review_id,
                "source_row_index": s.source_row_index,
                "sentence_text": s.sentence_text,
                "start": s.start,
                "end": s.end,
                "confidence": s.confidence,
            }
            for s in ordered_sents[:n_verbatims]
        ]

        # Titles and keywords
        if cid == -1:
            title = "Zero-Day Outlier Radar"
            kws = ["unclassified", "novel-defect", "emerging"]
            label_provenance = "HDBSCAN density outlier pool: emerging or non-standard complaints"
            outlier_share = count / max(n, 1)
            severity = "HIGH" if (outlier_share >= 0.10 and count >= 3) else "MEDIUM"
        else:
            kws = keywords_map.get(cid, [])
            if len(kws) >= 2:
                title = f"{kws[0].title()} & {kws[1].title()}"
                label_provenance = "c-TF-IDF over cluster member sentences"
            elif len(kws) == 1:
                title = kws[0].title()
                label_provenance = "c-TF-IDF (single dominant term)"
            else:
                title = f"Defect Pattern #{cid + 1}"
                label_provenance = "Fallback cluster designation"
            severity = classify_complaint_severity(count, total_complaints=n)

        # Statistical Causal Attribution / Relative Risk
        attribution = _compute_relative_risk(sents, review_metadata)

        clusters.append({
            "cluster_id": int(cid),
            "title": title,
            "label_provenance": label_provenance,
            "keywords": kws,
            "complaint_drivers": kws,
            "sentence_count": count,
            "severity": severity,
            "medoid_verbatim": medoid_sent.sentence_text,
            "affected_batch": attribution["affected_batch"],
            "relative_risk": attribution["relative_risk"],
            "is_statistically_significant": attribution["is_statistically_significant"],
            "verbatims": verbatims,
            "is_provisional": True,
        })

    # Sort regular clusters by volume, keep Zero-Day Outlier at top or designated location
    clusters.sort(key=lambda c: (c["cluster_id"] == -1, c["sentence_count"]), reverse=True)

    return {
        "clusters": clusters,
        "n_complaint_sentences": n,
        "n_clusters_actual": len(clusters),
        "clustering_mode": "hdbscan" if (mode == "hdbscan" and HDBSCAN_AVAILABLE) else "minibatch_kmeans",
        "is_provisional": True,
        "provisional_notices": [
            "Complaint clusters are unsupervised (MiniLM + MiniBatchKMeans / HDBSCAN). "
            "Cluster labels are NOT human-annotated.",
            "Cluster titles and keywords are class-based TF-IDF (c-TF-IDF) terms "
            "computed over each cluster's own member sentences.",
        ],
    }


def cluster_feature_requests(
    recommendation_sentences: List[SentenceRecord],
    n_clusters: int = 4,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Cluster the RECOMMENDATION sentences pool into structured feature request themes.

    Builds the 'Customer Wishlist' / Product Backlog items directly from customer verbatims.
    """
    n = len(recommendation_sentences)
    if n == 0:
        return {
            "feature_requests": [],
            "total_recommendations": 0,
            "n_clusters_actual": 0,
        }

    k = max(1, min(n_clusters, max(1, n // 4), n))
    texts = [s.sentence_text for s in recommendation_sentences]
    embeddings = embed_sentences(texts, cache_key_suffix=f"_recs_k{k}")

    kmeans = MiniBatchKMeans(
        n_clusters=k,
        random_state=random_state,
        batch_size=min(64, n),
        n_init=3,
    )
    labels = kmeans.fit_predict(embeddings)

    cluster_sentence_map: Dict[int, List[SentenceRecord]] = {c: [] for c in range(k)}
    for sent, cid in zip(recommendation_sentences, labels):
        cluster_sentence_map[int(cid)].append(sent)

    cluster_texts_map = {c: [s.sentence_text for s in sents] for c, sents in cluster_sentence_map.items()}
    keywords_map = extract_ctfidf_keywords(cluster_texts_map, top_n=6)

    feature_requests = []
    for cid in range(k):
        sents = cluster_sentence_map[cid]
        count = len(sents)
        if count == 0:
            continue

        cluster_indices = [i for i, lbl in enumerate(labels) if lbl == cid]
        c_embs = embeddings[cluster_indices]
        centroid = kmeans.cluster_centers_[cid]
        dists = np.linalg.norm(c_embs - centroid, axis=1)
        medoid_sent = recommendation_sentences[cluster_indices[int(np.argmin(dists))]]

        kws = keywords_map.get(cid, [])
        title = f"{kws[0].title()} & {kws[1].title()} Request" if len(kws) >= 2 else (kws[0].title() if kws else f"Feature Proposal #{cid + 1}")

        share = count / max(n, 1)
        priority = "HIGH" if (share >= 0.28 and count >= 2) else ("MEDIUM" if share >= 0.16 else "LOW")

        feature_requests.append({
            "request_id": cid,
            "title": title,
            "keywords": kws,
            "feature_themes": kws,
            "vote_count": count,
            "priority": priority,
            "medoid_quote": medoid_sent.sentence_text,
            "sample_quotes": [
                {
                    "sentence_id": s.sentence_id,
                    "review_id": s.review_id,
                    "sentence_text": s.sentence_text,
                    "start": s.start,
                    "end": s.end,
                }
                for s in sents[:5]
            ],
        })

    feature_requests.sort(key=lambda x: x["vote_count"], reverse=True)
    return {
        "feature_requests": feature_requests,
        "total_recommendations": n,
        "n_clusters_actual": len(feature_requests),
    }


def cluster_praise_sentences(
    praise_sentences: List[SentenceRecord],
    n_clusters: int = 5,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Cluster the PRAISE sentences pool into structured product strength themes.

    Surfaces 'Product Strengths' / Delight drivers directly from customer verbatims.
    Uses MiniLM sentence embeddings + MiniBatchKMeans + c-TF-IDF keyword extraction.
    """
    n = len(praise_sentences)
    if n == 0:
        return {
            "clusters": [],
            "praise_clusters": [],
            "total_praise": 0,
            "n_clusters_actual": 0,
        }

    k = max(1, min(n_clusters, max(1, n // 4), n))
    texts = [s.sentence_text for s in praise_sentences]
    embeddings = embed_sentences(texts, cache_key_suffix=f"_praise_k{k}")

    kmeans = MiniBatchKMeans(
        n_clusters=k,
        random_state=random_state,
        batch_size=min(64, n),
        n_init=3,
    )
    labels = kmeans.fit_predict(embeddings)

    cluster_sentence_map: Dict[int, List[SentenceRecord]] = {c: [] for c in range(k)}
    for sent, cid in zip(praise_sentences, labels):
        cluster_sentence_map[int(cid)].append(sent)

    cluster_texts_map = {c: [s.sentence_text for s in sents] for c, sents in cluster_sentence_map.items()}
    keywords_map = extract_ctfidf_keywords(cluster_texts_map, top_n=6)

    praise_clusters = []
    for cid in range(k):
        sents = cluster_sentence_map[cid]
        count = len(sents)
        if count == 0:
            continue

        cluster_indices = [i for i, lbl in enumerate(labels) if lbl == cid]
        c_embs = embeddings[cluster_indices]
        centroid = kmeans.cluster_centers_[cid]
        dists = np.linalg.norm(c_embs - centroid, axis=1)
        medoid_sent = praise_sentences[cluster_indices[int(np.argmin(dists))]]

        kws = keywords_map.get(cid, [])
        if len(kws) >= 2:
            title = f"{kws[0].title()} & {kws[1].title()}"
        elif len(kws) == 1:
            title = kws[0].title()
        else:
            title = f"Product Strength #{cid + 1}"

        # Average confidence for delight metric
        avg_confidence = float(np.mean([s.confidence for s in sents])) if sents else 0.85
        delight_score = round(avg_confidence * 100, 1)
        share = count / max(n, 1)
        delight_tier = "EXCEPTIONAL" if (share >= 0.28 and count >= 3) else ("STRONG" if share >= 0.15 else "NOTABLE")

        ordered_sents = [medoid_sent] + [s for s in sents if s.sentence_id != medoid_sent.sentence_id]
        verbatims = [
            {
                "sentence_id": s.sentence_id,
                "review_id": s.review_id,
                "source_row_index": s.source_row_index,
                "sentence_text": s.sentence_text,
                "start": s.start,
                "end": s.end,
                "confidence": s.confidence,
            }
            for s in ordered_sents[:10]
        ]

        praise_clusters.append({
            "cluster_id": cid,
            "title": title,
            "strength_drivers": kws,
            "keywords": kws,
            "sentence_count": count,
            "praise_count": count,
            "delight_score": delight_score,
            "delight_tier": delight_tier,
            "medoid_verbatim": medoid_sent.sentence_text,
            "verbatims": verbatims,
            "is_provisional": True,
        })

    praise_clusters.sort(key=lambda x: x["praise_count"], reverse=True)
    return {
        "clusters": praise_clusters,
        "praise_clusters": praise_clusters,
        "total_praise": n,
        "n_clusters_actual": len(praise_clusters),
    }


__all__ = [
    "embed_sentences",
    "extract_ctfidf_keywords",
    "cluster_complaint_sentences",
    "cluster_feature_requests",
    "cluster_praise_sentences",
]


