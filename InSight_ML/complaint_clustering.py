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
  - c-TF-IDF keywords are distinctive within the complaint corpus, not
    validated root causes.
  - Cluster count is heuristic; optimal k requires human evaluation.
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from InSight_ML.sentence_pipeline import SentenceRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_DEFAULT_N_CLUSTERS = 6
_EMBEDDING_DIM = 384
_CACHE_DIR = Path(__file__).resolve().parent / "outputs" / "complaint_cluster_cache"

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

    # Content-addressable cache key
    sample_str = "".join(texts[:5]) + "".join(texts[-5:]) + str(len(texts)) + cache_key_suffix
    cache_key = hashlib.sha256(sample_str.encode()).hexdigest()[:16]
    cache_file = _CACHE_DIR / f"emb_{cache_key}.npy"

    if cache_file.exists():
        logger.debug("Embedding cache hit: %s", cache_file.name)
        return np.load(cache_file)

    encoder = _get_encoder()
    t0 = time.time()
    embeddings = encoder.encode(
        texts,
        batch_size=128,
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

from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS

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

    c-TF-IDF penalizes terms that appear uniformly across all clusters and
    surfaces terms that are distinctively high in a specific cluster.

    Args:
        cluster_texts: {cluster_id: [list of sentence texts in this cluster]}
        top_n: Number of top keywords to return per cluster.

    Returns:
        {cluster_id: [keyword, ...]} — sorted by descending c-TF-IDF score.
    """
    cluster_ids = sorted(cluster_texts.keys())
    docs = [" ".join(cluster_texts[c]) for c in cluster_ids]

    if not any(d.strip() for d in docs):
        return {c: [] for c in cluster_ids}

    try:
        vectorizer = TfidfVectorizer(
            max_features=3000,
            ngram_range=(1, 2),
            stop_words=_COMBINED_STOPWORDS,
            min_df=1,
        )
        ctfidf_matrix = vectorizer.fit_transform(docs)
        feature_names = np.array(vectorizer.get_feature_names_out())
    except ValueError:
        # Fall back to standard english stop words if domain filtering eliminated all words
        try:
            vectorizer = TfidfVectorizer(
                max_features=3000,
                ngram_range=(1, 2),
                stop_words="english",
                min_df=1,
            )
            ctfidf_matrix = vectorizer.fit_transform(docs)
            feature_names = np.array(vectorizer.get_feature_names_out())
        except Exception as exc:
            logger.warning("c-TF-IDF vectorization fallback failed: %s", exc)
            return {c: [] for c in cluster_ids}
    except Exception as exc:
        logger.warning("c-TF-IDF vectorization failed: %s", exc)
        return {c: [] for c in cluster_ids}

    keywords: Dict[int, List[str]] = {}
    for doc_idx, c_id in enumerate(cluster_ids):
        row = ctfidf_matrix[doc_idx].toarray()[0]
        top_indices = row.argsort()[::-1][:top_n]
        keywords[c_id] = feature_names[top_indices].tolist()

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
          clusters        : List[Dict] — one entry per cluster, containing:
              cluster_id  : int
              title       : str — descriptive root-cause title
              keywords    : List[str] — c-TF-IDF root-cause keywords
              sentence_count : int
              severity    : str  (CRITICAL / HIGH / MEDIUM / LOW)
              medoid_verbatim: str — most central representative complaint sentence
              verbatims   : List[Dict] — up to 5 sentences with full traceability
          n_complaint_sentences : int
          n_clusters_actual     : int
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

    # Auto-scale cluster count
    k = max(2, min(n_clusters, n // 5, n))
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
        batch_size=min(256, n),
        n_init=3,
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
    keywords_map = extract_ctfidf_keywords(cluster_texts_map, top_n=8)

    # Step 5: Build cluster summaries with Medoid calculation & Defect Title
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
            for s in ordered_sents[:5]
        ]

        kws = keywords_map.get(cid, [])
        if len(kws) >= 2:
            title = f"{kws[0].title()} & {kws[1].title()}"
        elif len(kws) == 1:
            title = kws[0].title()
        else:
            title = f"Defect Mode #{cid + 1}"

        # Severity: purely based on cluster size and complaint nature
        # (all sentences here are already classified as COMPLAINT)
        if count >= 200:
            severity = "CRITICAL"
        elif count >= 80:
            severity = "HIGH"
        elif count >= 20:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        clusters.append({
            "cluster_id": cid,
            "title": title,
            "keywords": kws,
            "sentence_count": count,
            "severity": severity,
            "severity_note": (
                f"PROVISIONAL: severity={severity} based on complaint sentence count={count}. "
                "Thresholds: CRITICAL≥200, HIGH≥80, MEDIUM≥20, LOW<20. "
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
        "n_clusters_actual": k,
        "is_provisional": True,
        "provisional_notices": [
            "Complaint clusters are unsupervised (MiniLM + MiniBatchKMeans). "
            "Cluster labels are NOT human-annotated.",
            "c-TF-IDF keywords are statistically distinctive within the complaint corpus "
            "but have not been validated as true root causes.",
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
