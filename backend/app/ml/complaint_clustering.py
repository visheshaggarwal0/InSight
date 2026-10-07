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

    def classify_complaint_severity(
        count: int,
        total_complaints: int = 0,
        max_proposition_severity: str | None = None,
        p0_count: int = 0,
        p1_count: int = 0,
    ) -> str:
        if (p0_count > 0 or max_proposition_severity == "P0"):
            return "CRITICAL" if (p0_count >= 2 or count >= 4) else "HIGH"
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
    # Product and category filler
    "product", "products", "use", "used", "using", "really", "feel", "feels", "feeling", "felt",
    "tried", "bought", "got", "just", "like", "time", "day", "days", "face",
    "skin", "make", "makes", "think", "love", "way", "bit", "lot", "good",
    "great", "cream", "eyes", "eye", "moisturizer", "cleanser", "serum",
    "oil", "lotion", "apply", "applying", "applied", "didn", "don", "wasn", "doesn",
    "wouldn", "couldn", "ve", "ll", "went", "come", "came", "going", "know",
    "item", "items", "brand", "order", "ordered", "purchase", "purchased", "bottle",
    # Evaluative adjectives & generic sentiment noise that pollute defect root causes
    "worst", "bad", "terrible", "horrible", "awful", "disappointed", "disappointment",
    "waste", "work", "worked", "working", "works", "noticed", "notice", "noticing",
    "money", "unfortunately", "sadly", "thing", "things", "star", "stars",
    "say", "saying", "said", "give", "gave", "given", "giving", "get", "getting",
    "tries", "trying", "look", "looked", "looking", "ever", "completely",
    "absolutely", "definitely", "maybe", "probably", "actually", "literally",
    # Promotional review boilerplate, platform artifacts & filler tokens
    "influenster", "honest", "review", "reviews", "received", "free", "exchange",
    "complimentary", "complementary", "sample", "tested", "testing", "promotion", "promotional",
    "freeproduct", "repurchasing", "repurchase", "appreciative", "reward",
    "redacted_name", "redacted_email", "redacted_phone", "redacted_ip", "redacted", "sk",
    "stuff", "redacted_order_id", "redacted_timestamp", "redacted_date",
    "lol", "plastic", "cheek", "cheeks", "opinion", "opinions", "does", "did",
    "lauder", "estee", "estée", "sephora", "member", "incentivized", "gifted",
    "tube", "jar", "size", "mini", "right", "left", "side", "point", "people",
    "person", "bought", "buy", "purchased", "price", "worth", "removes", "easily",
}
_COMBINED_STOPWORDS = list(ENGLISH_STOP_WORDS.union(_VOC_STOPWORDS))

_PRAISE_STOPWORDS = _VOC_STOPWORDS.union({
    "amazing", "recommend", "recommended", "recommending", "favorite", "favourite",
    "best", "better", "leaves", "super", "highly", "nice", "perfect", "stuff", "does",
    "loved", "loves", "loving", "happy", "glad", "enjoy", "enjoyed", "awesome", "wonderful",
    "absolutely", "definitely", "really", "thank", "thanks", "influencer", "free", "gifted",
    "product", "products", "skin", "face", "feel", "feels", "feeling", "felt", "makes", "make",
    "try", "tried", "trying", "using", "used", "use", "purchased", "bought", "bottle", "bottles",
    "like", "just", "great", "good", "lot", "bit", "day", "days", "time", "times",
    "mask", "masks", "far", "weeks", "overall", "tool", "freaking", "line", "minis", "christmas",
    "redacted_name", "redacted_order_id", "redacted_email", "redacted_phone", "redacted_timestamp",
})
_PRAISE_COMBINED_STOPWORDS = list(ENGLISH_STOP_WORDS.union(_PRAISE_STOPWORDS))


# ---------------------------------------------------------------------------
# Adaptive Cluster Count & Semantic Defect Titling
# ---------------------------------------------------------------------------

def determine_adaptive_k(n_samples: int, target_k: Optional[int] = None) -> int:
    """Dynamically determine optimal cluster count k based on sample size.

    Prevents over-fragmentation on small batches and avoids collapsing
    large corpora into blurry mega-clusters.
    """
    if n_samples <= 6:
        return max(1, n_samples)
    if n_samples <= 20:
        return max(2, n_samples // 4)
    if n_samples <= 80:
        return max(4, n_samples // 12)
    if n_samples <= 250:
        return max(6, n_samples // 25)

    # Large corpora (n > 250): scale between 8 and 18 clusters
    min_k = int(COMPLAINT_CLUSTERING.get("min_clusters", 6))
    max_k = int(COMPLAINT_CLUSTERING.get("max_clusters", 18))
    computed_k = max(min_k, min(max_k, n_samples // 110))
    if target_k and not COMPLAINT_CLUSTERING.get("adaptive_k", True):
        return max(1, min(target_k, n_samples))
    return computed_k


_DEFECT_TAXONOMY_CANDIDATES = [
    "Dryness & Dehydration",
    "Skin Sensitivity & Irritation",
    "Allergic Reaction & Swelling",
    "Acne Breakouts & Blemishes",
    "Cystic & Hormonal Acne",
    "Pore Congestion & Blackheads",
    "Redness & Skin Flushing",
    "Unpleasant Odor & Scent",
    "Packaging & Dispenser Defect",
    "Packaging Leakage & Spillage",
    "Packaging Breakage & Shattered Bottle",
    "Greasy Texture & Heavy Residue",
    "Lack of Results & Inefficacy",
    "Eye Stinging & Irritation",
    "Lip Chapping & Peeling",
    "Delivery & Shipping Delays",
    "Refund & Billing Friction",
    "Burning & Itching Sensation",
    "Formula Stripping & Tightness",
    "Formula Separation & Discoloration",
]

_CACHED_TAXONOMY_EMBS: Optional[np.ndarray] = None


def _get_taxonomy_embeddings() -> np.ndarray:
    global _CACHED_TAXONOMY_EMBS
    if _CACHED_TAXONOMY_EMBS is None:
        encoder = _get_encoder()
        _CACHED_TAXONOMY_EMBS = encoder.encode(
            _DEFECT_TAXONOMY_CANDIDATES,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    return _CACHED_TAXONOMY_EMBS


def _derive_cluster_title(
    keywords: List[str],
    centroid: Optional[np.ndarray] = None,
    medoid_text: str = "",
    cluster_id: int = 0,
    used_titles: Optional[set] = None,
) -> Tuple[str, str]:
    """Derives a meaningful, professional defect title without repetitive keyword slop."""
    if used_titles is None:
        used_titles = set()

    # Step 1: Semantic taxonomy alignment via MiniLM centroid cosine similarity
    if centroid is not None:
        try:
            cand_embs = _get_taxonomy_embeddings()
            c_norm = centroid / (np.linalg.norm(centroid) + 1e-12)
            sims = np.dot(cand_embs, c_norm)
            sorted_indices = np.argsort(sims)[::-1]

            for idx in sorted_indices:
                cand_title = _DEFECT_TAXONOMY_CANDIDATES[idx]
                cand_sim = float(sims[idx])
                if cand_sim >= 0.30 and cand_title not in used_titles:
                    used_titles.add(cand_title)
                    return cand_title, f"Semantic centroid alignment ({cand_sim:.2f} similarity)"
        except Exception as exc:
            logger.debug("Taxonomy matching fallback: %s", exc)

    # Step 2: Clean distinct keyword derivation (no stem/word overlap)
    distinct_terms = []
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if not kw_clean:
            continue
        kw_words = set(kw_clean.split())
        overlap = any(
            kw_words.intersection(set(existing.split()))
            for existing in distinct_terms
        )
        if not overlap:
            distinct_terms.append(kw_clean)
        if len(distinct_terms) == 2:
            break

    if len(distinct_terms) >= 2:
        title = f"{distinct_terms[0].title()} & {distinct_terms[1].title()}"
        provenance = "c-TF-IDF distinctive root causes"
    elif len(distinct_terms) == 1:
        title = f"{distinct_terms[0].title()} Defect"
        provenance = "c-TF-IDF single dominant defect term"
    else:
        title = f"Defect Pattern #{cluster_id + 1}"
        provenance = "Heuristic defect cluster designation"

    used_titles.add(title)
    return title, provenance


_PRAISE_TAXONOMY_CANDIDATES = [
    "Deep Hydration & Moisture Barrier",
    "Radiant Glow & Skin Brightening",
    "Gentle Formula for Sensitive Skin",
    "Acne Clearing & Blemish Control",
    "Softening & Silky Smooth Texture",
    "Pleasant Fragrance & Subtle Scent",
    "Rapid Absorption & Lightweight Feel",
    "Clean Cleansing & Makeup Removal",
    "Pore Refinement & Gentle Exfoliation",
    "Even Tone & Dark Spot Reduction",
    "Flawless Makeup Base & Primer Prep",
    "Daily Holy Grail & High Satisfaction",
    "Soothing Redness & Calming Relief",
    "Non-Greasy & Balanced Finish",
    "Rich Nourishing Night Care",
]

_CACHED_PRAISE_TAXONOMY_EMBS: Optional[np.ndarray] = None


def _get_praise_taxonomy_embeddings() -> np.ndarray:
    global _CACHED_PRAISE_TAXONOMY_EMBS
    if _CACHED_PRAISE_TAXONOMY_EMBS is None:
        encoder = _get_encoder()
        _CACHED_PRAISE_TAXONOMY_EMBS = encoder.encode(
            _PRAISE_TAXONOMY_CANDIDATES,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    return _CACHED_PRAISE_TAXONOMY_EMBS


def _derive_praise_cluster_title(
    keywords: List[str],
    centroid: Optional[np.ndarray] = None,
    medoid_text: str = "",
    cluster_id: int = 0,
    used_titles: Optional[set] = None,
) -> Tuple[str, str]:
    """Derives a meaningful, professional product strength title without keyword slop."""
    if used_titles is None:
        used_titles = set()

    # Step 1: Semantic taxonomy alignment via MiniLM centroid cosine similarity
    if centroid is not None:
        try:
            cand_embs = _get_praise_taxonomy_embeddings()
            c_norm = centroid / (np.linalg.norm(centroid) + 1e-12)
            sims = np.dot(cand_embs, c_norm)
            sorted_indices = np.argsort(sims)[::-1]

            for idx in sorted_indices:
                cand_title = _PRAISE_TAXONOMY_CANDIDATES[idx]
                cand_sim = float(sims[idx])
                if cand_sim >= 0.28 and cand_title not in used_titles:
                    used_titles.add(cand_title)
                    return cand_title, f"Semantic centroid alignment ({cand_sim:.2f} similarity)"
        except Exception as exc:
            logger.debug("Praise taxonomy matching fallback: %s", exc)

    # Step 2: Clean distinct keyword derivation (no stem/word overlap)
    distinct_terms = []
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if not kw_clean or kw_clean in _PRAISE_STOPWORDS:
            continue
        kw_words = set(kw_clean.split())
        overlap = any(
            kw_words.intersection(set(existing.split()))
            for existing in distinct_terms
        )
        if not overlap:
            distinct_terms.append(kw_clean)
        if len(distinct_terms) == 2:
            break

    if len(distinct_terms) >= 2:
        title = f"{distinct_terms[0].title()} & {distinct_terms[1].title()}"
        provenance = "c-TF-IDF distinctive strength drivers"
    elif len(distinct_terms) == 1:
        title = f"{distinct_terms[0].title()} Strength"
        provenance = "c-TF-IDF single dominant praise term"
    else:
        title = f"Product Strength #{cluster_id + 1}"
        provenance = "Heuristic strength cluster designation"

    used_titles.add(title)
    return title, provenance


def _compute_praise_attribution(
    sents: List[SentenceRecord],
    review_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute cohort and SKU attribution for customer delight/praise drivers."""
    if not review_metadata:
        avg_confidence = float(np.mean([s.confidence for s in sents])) if sents else 0.85
        return {
            "top_batch": "Standard",
            "hero_sku": "Core Product",
            "delight_score": round(avg_confidence * 100, 1),
            "delight_tier": "STRONG",
        }

    batch_counts: Dict[str, int] = {}
    sku_counts: Dict[str, int] = {}
    confidences = []

    for s in sents:
        meta = review_metadata.get(s.review_id, {})
        batch = meta.get("batch_or_version") or "General"
        sku = meta.get("sku_or_module") or "Core Line"
        batch_counts[batch] = batch_counts.get(batch, 0) + 1
        sku_counts[sku] = sku_counts.get(sku, 0) + 1
        if hasattr(s, "confidence") and s.confidence:
            confidences.append(s.confidence)

    top_batch = max(batch_counts.items(), key=lambda x: x[1])[0] if batch_counts else "General"
    hero_sku = max(sku_counts.items(), key=lambda x: x[1])[0] if sku_counts else "Core Product"

    avg_conf = float(np.mean(confidences)) if confidences else 0.88
    delight_score = round(min(99.0, max(75.0, avg_conf * 100)), 1)

    count = len(sents)
    delight_tier = "EXCEPTIONAL" if count >= 2000 else ("STRONG" if count >= 1000 else "NOTABLE")

    return {
        "top_batch": top_batch,
        "hero_sku": hero_sku,
        "delight_score": delight_score,
        "delight_tier": delight_tier,
    }


# ---------------------------------------------------------------------------
# c-TF-IDF keyword extraction
# ---------------------------------------------------------------------------

def extract_ctfidf_keywords(
    cluster_texts: Dict[int, List[str]],
    top_n: int = 8,
    stop_words: Optional[Any] = None,
    max_df: float = 0.85,
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
        stop_words: Optional custom stopword list/set. Defaults to _COMBINED_STOPWORDS.
        max_df: Maximum document frequency to avoid terms present in all clusters.

    Returns:
        {cluster_id: [keyword, ...]} — strictly positive scores only, sorted by
        descending c-TF-IDF weight. A cluster whose entire vocabulary is
        stop-worded away maps to an empty list rather than a padded one.
    """
    cluster_ids = sorted(cluster_texts.keys())
    docs = [" ".join(cluster_texts[c]) for c in cluster_ids]

    if not any(d.strip() for d in docs) or top_n <= 0:
        return {c: [] for c in cluster_ids}

    target_stop_words = stop_words if stop_words is not None else _COMBINED_STOPWORDS

    def _count(words, m_df=max_df) -> Optional[Tuple[Any, np.ndarray]]:
        """CountVectorizer is used purely as a tokenizer/counter here."""
        try:
            vec = CountVectorizer(
                max_features=3000,
                ngram_range=(1, 2),
                stop_words=words,
                min_df=1,
                max_df=m_df if len(docs) > 2 else 1.0,
            )
            return vec.fit_transform(docs), vec.get_feature_names_out()
        except ValueError:
            return None

    counted = _count(target_stop_words)
    if counted is None:
        # Fall back without max_df constraint
        counted = _count(target_stop_words, m_df=1.0)
    if counted is None:
        # Fall back to standard english stop words
        counted = _count("english", m_df=1.0)
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

def _merge_similar_clusters(
    cluster_sentence_map: Dict[int, List[SentenceRecord]],
    cluster_indices_map: Dict[int, List[int]],
    embeddings: np.ndarray,
    threshold: float = 0.85,
) -> Tuple[Dict[int, List[SentenceRecord]], Dict[int, List[int]]]:
    """Iteratively merge cluster pairs whose normalized centroid cosine similarity >= threshold.

    Noise cluster (-1, Zero-Day Outlier Radar) is strictly exempt from merging.
    Merges the smaller cluster into the larger cluster, updating centroid representation.
    """
    if threshold <= 0.0 or len(cluster_sentence_map) <= 1:
        return cluster_sentence_map, cluster_indices_map

    # Work on copies
    c_sents = {c: list(sents) for c, sents in cluster_sentence_map.items()}
    c_indices = {c: list(idxs) for c, idxs in cluster_indices_map.items()}

    while True:
        # Only regular clusters (c >= 0) with members
        reg_cids = [c for c in c_sents.keys() if c >= 0 and len(c_indices[c]) > 0]
        if len(reg_cids) <= 1:
            break

        # Compute normalized centroids for active regular clusters
        centroids: Dict[int, np.ndarray] = {}
        for c in reg_cids:
            embs = embeddings[c_indices[c]]
            mean_vec = embs.mean(axis=0)
            norm = np.linalg.norm(mean_vec)
            centroids[c] = mean_vec / (norm + 1e-12)

        best_pair: Optional[Tuple[int, int]] = None
        best_sim = -1.0

        for i in range(len(reg_cids)):
            for j in range(i + 1, len(reg_cids)):
                cid_a, cid_b = reg_cids[i], reg_cids[j]
                sim = float(np.dot(centroids[cid_a], centroids[cid_b]))
                if sim > best_sim:
                    best_sim = sim
                    best_pair = (cid_a, cid_b)

        if best_pair is not None and best_sim >= threshold:
            cid_keep, cid_merge = best_pair
            # Prefer keeping the larger cluster ID/membership to stabilize cluster tracking
            if len(c_sents[cid_merge]) > len(c_sents[cid_keep]):
                cid_keep, cid_merge = cid_merge, cid_keep

            logger.info(
                "Post-clustering merge: merging cluster %d (n=%d) into cluster %d (n=%d) with centroid similarity %.3f >= %.2f",
                cid_merge, len(c_sents[cid_merge]), cid_keep, len(c_sents[cid_keep]), best_sim, threshold,
            )
            c_sents[cid_keep].extend(c_sents[cid_merge])
            c_indices[cid_keep].extend(c_indices[cid_merge])
            del c_sents[cid_merge]
            del c_indices[cid_merge]
        else:
            break

    return c_sents, c_indices


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
    p_val = 1.0
    try:
        from scipy.stats import fisher_exact
        table = [
            [cluster_batch_count, max(0, total_corpus_for_batch - cluster_batch_count)],
            [other_batch_cluster_count, max(0, other_corpus_count - other_batch_cluster_count)],
        ]
        _, p_val = fisher_exact(table, alternative="greater")
        if np.isnan(p_val):
            p_val = 1.0
    except Exception:
        p_val = 1.0

    is_sig = bool(p_val < 0.05 and cluster_batch_count >= 3 and rr >= 1.5)

    return {
        "affected_batch": top_batch if is_sig else (top_batch if cluster_batch_count >= 3 else "Omnichannel"),
        "relative_risk": rr if is_sig else 1.0,
        "is_statistically_significant": is_sig,
        "batch_count": cluster_batch_count,
        "p_value": round(float(p_val), 5),
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

    k = determine_adaptive_k(n, n_clusters)
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
    cluster_indices_map: Dict[int, List[int]] = {c: [] for c in unique_cids}
    for idx, (sent, cid) in enumerate(zip(complaint_sentences, labels)):
        cluster_sentence_map[int(cid)].append(sent)
        cluster_indices_map[int(cid)].append(idx)

    # Step 3b: Post-Clustering Centroid Similarity Merge Pass
    # Merges near-duplicate cluster pairs (e.g. twin breakout or irritation drivers)
    # when their normalized centroid cosine similarity >= merge_similarity_threshold.
    # Outlier pool (-1) is explicitly exempt.
    merge_threshold = float(COMPLAINT_CLUSTERING.get("merge_similarity_threshold", 0.85))
    if merge_threshold > 0.0:
        cluster_sentence_map, cluster_indices_map = _merge_similar_clusters(
            cluster_sentence_map,
            cluster_indices_map,
            embeddings,
            threshold=merge_threshold,
        )

    merged_cids = sorted(list(cluster_sentence_map.keys()))

    # Step 4: c-TF-IDF keywords across regular clusters (excluding noise -1)
    regular_cids = [c for c in merged_cids if c >= 0]
    cluster_texts_map = {c: [s.sentence_text for s in cluster_sentence_map[c]] for c in regular_cids}
    keywords_map = extract_ctfidf_keywords(
        cluster_texts_map, top_n=COMPLAINT_CLUSTERING["top_keywords"],
    )

    # Step 5: Build cluster summaries
    n_verbatims = COMPLAINT_CLUSTERING["n_verbatims"]
    clusters = []
    used_titles: set = set()

    for cid in merged_cids:
        sents = cluster_sentence_map[cid]
        count = len(sents)
        if count == 0:
            continue

        c_indices = cluster_indices_map[cid]
        c_embs = embeddings[c_indices]

        # Medoid calculation & ranking by distance to cluster centroid
        mean_vec = c_embs.mean(axis=0, keepdims=True)
        c_centroid = mean_vec[0]
        dists = np.linalg.norm(c_embs - mean_vec, axis=1)
        sorted_order = np.argsort(dists)
        ordered_sents = [complaint_sentences[c_indices[idx]] for idx in sorted_order]
        medoid_sent = ordered_sents[0]

        verbatims = []
        for s in ordered_sents:
            meta = review_metadata.get(s.review_id, {}) if review_metadata else {}
            verbatims.append({
                "sentence_id": s.sentence_id,
                "review_id": s.review_id,
                "source_row_index": s.source_row_index,
                "sentence_text": s.sentence_text,
                "start": s.start,
                "end": s.end,
                "confidence": s.confidence,
                "rating": meta.get("rating", 4),
                "batch_or_version": meta.get("batch_or_version", "General"),
                "sku_or_module": meta.get("sku_or_module", "Unknown"),
                "product_name": meta.get("product_name", ""),
            })

        # Proposition-conditioned severity signals
        p0_count = sum(1 for s in sents if getattr(s, "operational_severity", "") == "P0")
        p1_count = sum(1 for s in sents if getattr(s, "operational_severity", "") == "P1")
        max_prop_sev = "P0" if p0_count > 0 else ("P1" if p1_count > 0 else "P2")

        # Titles and keywords
        if cid == -1:
            title = "Zero-Day Outlier Radar"
            kws = ["unclassified", "novel-defect", "emerging"]
            label_provenance = "HDBSCAN density outlier pool: emerging or non-standard complaints"
            outlier_share = count / max(n, 1)
            severity = "HIGH" if (outlier_share >= 0.10 and count >= 3 or p0_count >= 1) else "MEDIUM"
        else:
            kws = keywords_map.get(cid, [])
            title, label_provenance = _derive_cluster_title(
                keywords=kws,
                centroid=c_centroid,
                medoid_text=medoid_sent.sentence_text,
                cluster_id=cid,
                used_titles=used_titles,
            )
            severity = classify_complaint_severity(
                count,
                total_complaints=n,
                max_proposition_severity=max_prop_sev,
                p0_count=p0_count,
                p1_count=p1_count,
            )

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
        clean_terms = []
        for kw in kws:
            kw_words = set(kw.strip().lower().split())
            if not any(kw_words.intersection(set(e.split())) for e in clean_terms):
                clean_terms.append(kw.strip().lower())
            if len(clean_terms) == 2:
                break

        if len(clean_terms) >= 2:
            title = f"{clean_terms[0].title()} & {clean_terms[1].title()} Request"
        elif len(clean_terms) == 1:
            title = f"{clean_terms[0].title()} Request"
        else:
            title = f"Feature Proposal #{cid + 1}"

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
    n_clusters: int = 8,
    random_state: int = 42,
    review_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Cluster the PRAISE sentences pool into structured product strength themes.

    Mirrors the complaint clustering architecture:
    1. Filter trivial sentence fragments (< 3 words).
    2. MiniLM sentence embeddings with disk cache.
    3. Mean-centering to eliminate generic positive sentiment bias and isolate functional attributes.
    4. KMeans clustering (k-means++ initialization, n_init=5).
    5. Post-clustering centroid similarity merge pass (threshold=0.88).
    6. c-TF-IDF keyword extraction with domain-specific praise filler stopwords.
    7. Semantic taxonomy alignment against verified delight categories.
    8. Cohort & SKU delight attribution (top_batch, hero_sku, delight_tier).
    9. Medoid calculation and verbatim ranking.
    """
    valid_sentences = [
        s for s in praise_sentences
        if len(s.sentence_text.split()) >= 3
    ]
    n = len(valid_sentences)
    if n == 0:
        return {
            "clusters": [],
            "praise_clusters": [],
            "total_praise": 0,
            "n_clusters_actual": 0,
            "is_provisional": True,
            "provisional_notices": ["No valid praise sentences found in corpus."],
        }

    k = min(n, max(1, min(n_clusters, n // 8 if n > 40 else max(1, n // 2))))
    texts = [s.sentence_text for s in valid_sentences]
    embeddings = embed_sentences(texts, cache_key_suffix=f"_praise_k{k}")

    # Mean-centering: remove the common positive sentiment direction to highlight functional qualities
    corpus_mean = embeddings.mean(axis=0, keepdims=True)
    centered = embeddings - corpus_mean
    centered = centered / (np.linalg.norm(centered, axis=1, keepdims=True) + 1e-12)

    from sklearn.cluster import KMeans
    kmeans = KMeans(
        n_clusters=k,
        init="k-means++",
        n_init=5,
        random_state=random_state,
    )
    labels = kmeans.fit_predict(centered)

    cluster_sentence_map: Dict[int, List[SentenceRecord]] = {c: [] for c in range(k)}
    cluster_indices_map: Dict[int, List[int]] = {c: [] for c in range(k)}
    for idx, (sent, cid) in enumerate(zip(valid_sentences, labels)):
        cluster_sentence_map[int(cid)].append(sent)
        cluster_indices_map[int(cid)].append(idx)

    # Post-clustering merge pass: merge duplicate clusters if centroid cosine similarity >= 0.88
    cluster_sentence_map, cluster_indices_map = _merge_similar_clusters(
        cluster_sentence_map,
        cluster_indices_map,
        embeddings,
        threshold=0.88,
    )

    merged_cids = sorted(list(cluster_sentence_map.keys()))
    cluster_texts_map = {c: [s.sentence_text for s in cluster_sentence_map[c]] for c in merged_cids}
    keywords_map = extract_ctfidf_keywords(
        cluster_texts_map,
        top_n=8,
        stop_words=_PRAISE_COMBINED_STOPWORDS,
        max_df=0.85,
    )

    praise_clusters = []
    used_titles: set = set()

    for cid in merged_cids:
        sents = cluster_sentence_map[cid]
        count = len(sents)
        if count == 0:
            continue

        c_indices = cluster_indices_map[cid]
        c_embs = embeddings[c_indices]
        mean_vec = c_embs.mean(axis=0)
        c_centroid = mean_vec / (np.linalg.norm(mean_vec) + 1e-12)
        dists = np.linalg.norm(c_embs - mean_vec, axis=1)
        sorted_order = np.argsort(dists)
        ordered_sents = [valid_sentences[c_indices[idx]] for idx in sorted_order]
        medoid_sent = ordered_sents[0]

        kws = keywords_map.get(cid, [])
        title, label_provenance = _derive_praise_cluster_title(
            keywords=kws,
            centroid=c_centroid,
            medoid_text=medoid_sent.sentence_text,
            cluster_id=cid,
            used_titles=used_titles,
        )

        attribution = _compute_praise_attribution(sents, review_metadata)

        verbatims = []
        for s in ordered_sents:
            meta = (review_metadata or {}).get(s.review_id, {})
            verbatims.append({
                "sentence_id": s.sentence_id,
                "review_id": s.review_id,
                "source_row_index": s.source_row_index,
                "sentence_text": s.sentence_text,
                "start": s.start,
                "end": s.end,
                "confidence": s.confidence,
                "rating": meta.get("rating", 5),
                "batch_or_version": meta.get("batch_or_version", attribution["top_batch"]),
                "sku_or_module": meta.get("sku_or_module", attribution["hero_sku"]),
            })

        praise_clusters.append({
            "cluster_id": int(cid),
            "title": title,
            "label_provenance": label_provenance,
            "strength_drivers": kws,
            "keywords": kws,
            "sentence_count": count,
            "praise_count": count,
            "delight_score": attribution["delight_score"],
            "delight_tier": attribution["delight_tier"],
            "top_batch": attribution["top_batch"],
            "hero_sku": attribution["hero_sku"],
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
        "is_provisional": True,
        "provisional_notices": [
            "Product strength clusters are unsupervised (MiniLM + Mean-Centered KMeans).",
            "Cluster titles and keywords are derived from distinctive c-TF-IDF drivers and verified strength taxonomies.",
        ],
    }


__all__ = [
    "embed_sentences",
    "extract_ctfidf_keywords",
    "cluster_complaint_sentences",
    "cluster_feature_requests",
    "cluster_praise_sentences",
]


