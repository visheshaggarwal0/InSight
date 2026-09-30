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
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

try:
    from app.ml.sentence_pipeline import SentenceRecord
except ImportError:
    from InSight_ML.sentence_pipeline import SentenceRecord

try:
    from app.ml.pipeline_config import COMPLAINT_CLUSTERING, embedding_cache_key
except ImportError:
    from InSight_ML.pipeline_config import COMPLAINT_CLUSTERING, embedding_cache_key

try:
    from app.ml.severity import classify_complaint_severity
except ImportError:  # pragma: no cover - only if app.ml is not importable
    # Single source of truth is app.ml.severity. This fallback exists only so a
    # broken/mis-installed backend cannot make the whole ml package unimportable;
    # it reads the SAME thresholds from pipeline_config.
    _SEV = COMPLAINT_CLUSTERING["severity_thresholds"]

    def classify_complaint_severity(count: int) -> str:
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

def cluster_complaint_sentences(
    complaint_sentences: List[SentenceRecord],
    n_clusters: int = _DEFAULT_N_CLUSTERS,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Embed, cluster, and summarize complaint sentences.

    Args:
        complaint_sentences: Sentences from the COMPLAINT pool.
        n_clusters: Desired number of root-cause clusters (auto-scaled down
            if corpus is small).
        random_state: For MiniBatchKMeans reproducibility.

    Returns:
        A dict with:
          clusters        : List[Dict] — one entry per NON-EMPTY cluster:
              cluster_id  : int
              title       : str — descriptive label derived from c-TF-IDF keywords
              label_provenance : str — how the title was produced
              keywords    : List[str] — class-based TF-IDF (c-TF-IDF) keywords
              sentence_count : int
              severity    : str  (CRITICAL / HIGH / MEDIUM / LOW)
              medoid_verbatim: str — most central representative complaint sentence
              verbatims   : List[Dict] — up to COMPLAINT_CLUSTERING["n_verbatims"]
                            sentences with full traceability
          n_complaint_sentences : int
          n_clusters_actual     : int — the OBSERVED number of non-empty clusters
          is_provisional        : True
          provisional_notices   : List[str]
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

    # Auto-scale cluster count. The inner max(1, ...) matters: for n < 5 the
    # integer division n // 5 is 0, which previously produced k = 2 > n and a
    # reported n_clusters_actual that did not match the clusters returned.
    k = max(1, min(n_clusters, max(1, n // 5), n))
    if k != n_clusters:
        logger.info(
            "Complaint clustering: auto-scaled k from %d → %d (corpus size=%d)",
            n_clusters, k, n,
        )

    texts = [s.sentence_text for s in complaint_sentences]

    # Step 1: MiniLM embeddings (384-d, L2-normalized)
    logger.info("Complaint clustering: embedding %d complaint sentences …", n)
    embeddings = embed_sentences(texts, cache_key_suffix=f"_k{k}")

    # Step 2: MiniBatchKMeans
    logger.info("Complaint clustering: fitting MiniBatchKMeans(k=%d) …", k)
    kmeans = MiniBatchKMeans(
        n_clusters=k,
        random_state=random_state,
        batch_size=min(COMPLAINT_CLUSTERING["batch_size"], n),
        n_init=COMPLAINT_CLUSTERING["n_init"],
    )
    t0 = time.time()
    labels = kmeans.fit_predict(embeddings)
    logger.info("  KMeans fit in %.2fs", time.time() - t0)

    # Step 3: Group sentences by cluster
    cluster_sentence_map: Dict[int, List[SentenceRecord]] = {c: [] for c in range(k)}
    for sent, cid in zip(complaint_sentences, labels):
        cluster_sentence_map[int(cid)].append(sent)

    # Step 4: c-TF-IDF keywords
    cluster_texts_map = {c: [s.sentence_text for s in sents] for c, sents in cluster_sentence_map.items()}
    keywords_map = extract_ctfidf_keywords(
        cluster_texts_map, top_n=COMPLAINT_CLUSTERING["top_keywords"],
    )

    # Step 5: Build cluster summaries with Medoid calculation & Defect Title
    n_verbatims = COMPLAINT_CLUSTERING["n_verbatims"]
    sev_thresholds = COMPLAINT_CLUSTERING["severity_thresholds"]
    clusters = []
    for cid in range(k):
        sents = cluster_sentence_map[cid]
        count = len(sents)
        if count == 0:
            continue

        # Medoid calculation: find sentence closest to the cluster centroid
        cluster_indices = [i for i, lbl in enumerate(labels) if lbl == cid]
        if cluster_indices:
            c_embs = embeddings[cluster_indices]
            centroid = kmeans.cluster_centers_[cid]
            dists = np.linalg.norm(c_embs - centroid, axis=1)
            medoid_local_idx = int(np.argmin(dists))
            medoid_sent = complaint_sentences[cluster_indices[medoid_local_idx]]
        else:
            medoid_sent = sents[0]

        # Prioritize medoid at index 0 for verbatim traceability
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

        # Defensive title construction. Filtering zero-score c-TF-IDF terms
        # (see extract_ctfidf_keywords) means a cluster can now legitimately
        # surface 0 or 1 keywords, so kws[0] / kws[1] must never be indexed
        # unconditionally.
        kws = keywords_map.get(cid, [])
        if len(kws) >= 2:
            title = f"{kws[0].title()} & {kws[1].title()}"
            label_provenance = (
                "c-TF-IDF over this cluster's own member sentences "
                "(descriptive, not causal)"
            )
        elif len(kws) == 1:
            title = kws[0].title()
            label_provenance = (
                "c-TF-IDF over this cluster's own member sentences "
                "(descriptive, not causal; only one term carried positive weight)"
            )
        else:
            title = f"Defect Mode #{cid + 1}"
            label_provenance = (
                "fallback: no c-TF-IDF term in this cluster carried positive weight"
            )

        # Severity: purely based on cluster size and complaint nature
        # (all sentences here are already classified as COMPLAINT). Delegated to
        # app.ml.severity so there is exactly ONE severity implementation and
        # the cutoffs live only in pipeline_config.
        severity = classify_complaint_severity(count)

        clusters.append({
            "cluster_id": cid,
            "title": title,
            "label_provenance": label_provenance,
            "keywords": kws,
            "sentence_count": count,
            "severity": severity,
            "severity_note": (
                f"PROVISIONAL: severity={severity} based on complaint sentence count={count}. "
                f"Thresholds: CRITICAL≥{sev_thresholds['critical']}, "
                f"HIGH≥{sev_thresholds['high']}, "
                f"MEDIUM≥{sev_thresholds['medium']}, "
                f"LOW<{sev_thresholds['medium']}. "
                "Not statistically validated for this domain."
            ),
            "medoid_verbatim": medoid_sent.sentence_text,
            "verbatims": verbatims,
            "is_provisional": True,
        })

    # Sort by sentence count descending (largest / most-cited complaint first)
    clusters.sort(key=lambda c: c["sentence_count"], reverse=True)

    return {
        "clusters": clusters,
        "n_complaint_sentences": n,
        # Report what was OBSERVED, not what was requested: empty clusters are
        # skipped above, so `k` can overstate the number of clusters returned.
        "n_clusters_actual": len(clusters),
        "is_provisional": True,
        "provisional_notices": [
            "Complaint clusters are unsupervised (MiniLM + MiniBatchKMeans). "
            "Cluster labels are NOT human-annotated.",
            "Cluster titles and keywords are class-based TF-IDF (c-TF-IDF) terms "
            "computed over each cluster's own member sentences, so they restate the "
            "cluster definition. They are descriptive, not causal, and are not "
            "validated root causes.",
            "Cluster count k is heuristically determined. Optimal k requires human evaluation.",
            "Sentence classification is heuristic (regex). "
            "No precision/recall measured against labelled complaint sentences.",
        ],
    }


__all__ = [
    "embed_sentences",
    "extract_ctfidf_keywords",
    "cluster_complaint_sentences",
]
