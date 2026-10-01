"""clustering.py
Unsupervised thematic clustering for review-level data.

Dense vectors come from all-MiniLM-L6-v2 when available (loaded LAZILY - see
get_encoder()), otherwise from a TF-IDF fallback. Cluster keywords are
class-based TF-IDF (c-TF-IDF) terms over the clusters themselves.

Clustering mode is controlled by ``pipeline_config.CLUSTERING_MODE``:
  "kmeans"  — MiniBatchKMeans (default; always available; requires n_clusters)
  "hdbscan" — UMAP dimensionality reduction + HDBSCAN density clustering.
              Automatically discovers cluster count. Points that do not belong
              to any dense cluster are assigned cluster_id = -1 and surfaced in
              the dashboard as an "Uncategorised / Zero-Day" theme.
              Falls back to KMeans if ``hdbscan`` or ``umap`` are not installed.
"""

import importlib.util
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    from app.ml.pipeline_config import (
        THEME, CLUSTERING_MODE, HDBSCAN_CONFIG, embedding_cache_key
    )
except ImportError:  # pragma: no cover - InSight_ML shim import path
    from InSight_ML.pipeline_config import (
        THEME, CLUSTERING_MODE, HDBSCAN_CONFIG, embedding_cache_key
    )

try:
    from app.ml.severity import classify_severity, corpus_negative_fraction
except ImportError:  # pragma: no cover - only if app.ml is not importable
    classify_severity = None
    corpus_negative_fraction = None

logger = logging.getLogger(__name__)

# Fully-qualified model id. The bare short name 'all-MiniLM-L6-v2' resolves to a
# DIFFERENT HuggingFace cache key for the exact same weights, so a process that
# mixes the two downloads the model twice.
MODEL_NAME: str = THEME["model_name"]
EMBEDDING_DIM: int = 384

# Cheap check only: does the library import?  This must NOT construct a model —
# app.ml.clustering is imported by app.ml.__init__, which app/api/routes.py and
# InSight_ML/__init__.py both trigger, so a model load here cost every caller a
# ~90 MB download and a multi-second stall at import time.
TRANSFORMER_AVAILABLE: bool = importlib.util.find_spec("sentence_transformers") is not None

# Optional density-clustering libraries — checked once at module load.
HDBSCAN_AVAILABLE: bool = (
    importlib.util.find_spec("hdbscan") is not None
    and importlib.util.find_spec("umap") is not None
)

_ENCODER = None
_ENCODER_UNAVAILABLE = False
_ENCODER_LOCK = threading.Lock()


def get_encoder(model_name: Optional[str] = None):
    """Load the MiniLM bi-encoder on first use and cache it (lazy singleton).

    Returns:
        A loaded ``SentenceTransformer``, or ``None`` if it cannot be loaded
        (e.g. no cached weights and no network). Callers must handle ``None``.
    """
    global _ENCODER, _ENCODER_UNAVAILABLE

    if _ENCODER is not None:
        return _ENCODER
    if _ENCODER_UNAVAILABLE:
        return None

    name = model_name or MODEL_NAME
    with _ENCODER_LOCK:
        if _ENCODER is not None:
            return _ENCODER
        if _ENCODER_UNAVAILABLE:
            return None
        t0 = time.time()
        try:
            from sentence_transformers import SentenceTransformer

            _ENCODER = SentenceTransformer(name)
        except Exception as exc:
            _ENCODER_UNAVAILABLE = True
            logger.warning(
                "SentenceTransformer('%s') could not be loaded, falling back to TF-IDF: %s",
                name,
                exc,
            )
            return None
        logger.info(
            "SentenceTransformer ('%s') lazily loaded in %.2fs for dense clustering.",
            name,
            time.time() - t0,
        )
        return _ENCODER


def reset_encoder_cache() -> None:
    """Drop the cached encoder so the next get_encoder() call retries."""
    global _ENCODER, _ENCODER_UNAVAILABLE
    with _ENCODER_LOCK:
        _ENCODER = None
        _ENCODER_UNAVAILABLE = False


class _LazyTransformerEncoder:
    """Import-safe stand-in for a ``SentenceTransformer`` instance.

    ``backend/app/api/routes.py`` does ``from app.ml.clustering import
    transformer_encoder`` at MODULE scope and then uses it as an object
    (``transformer_encoder.encode(...)``). The name therefore cannot be removed
    and cannot simply be ``None`` at import time - routes.py would bind ``None``
    into its own namespace permanently and semantic search would 503 forever.

    So the name is preserved as a proxy that loads the real weights on the first
    attribute access. ``routes.py``'s ``if transformer_encoder is None`` guard is
    now always False; the lazy load happens inside its existing try/except and a
    load failure surfaces as a 500 ("Semantic search failed") instead of a 503.
    """

    __slots__ = ()

    def _resolve(self):
        encoder = get_encoder()
        if encoder is None:
            raise RuntimeError(
                f"SentenceTransformer encoder '{MODEL_NAME}' is unavailable "
                "(library missing, or weights not cached and no network). "
                "Run 'python scripts/download_models.py' while online."
            )
        return encoder

    def __getattr__(self, item):
        return getattr(self._resolve(), item)

    def __repr__(self):  # pragma: no cover - debugging aid
        state = "loaded" if _ENCODER is not None else "not loaded"
        return f"<LazyTransformerEncoder {MODEL_NAME!r} ({state})>"


# Kept for import compatibility (routes.py, scripts/seed_neon_db.py).
transformer_encoder = _LazyTransformerEncoder()


# ---------------------------------------------------------------------------
# UMAP + HDBSCAN helpers
# ---------------------------------------------------------------------------

def _umap_reduce(X: np.ndarray) -> np.ndarray:
    """Apply UMAP dimensionality reduction using HDBSCAN_CONFIG parameters.

    Args:
        X: Dense embedding matrix (n_samples, embedding_dim).

    Returns:
        Reduced matrix (n_samples, umap_n_components).

    Raises:
        ImportError: If ``umap-learn`` is not installed.
    """
    import umap  # type: ignore[import]

    reducer = umap.UMAP(
        n_components=HDBSCAN_CONFIG["umap_n_components"],
        metric=HDBSCAN_CONFIG["umap_metric"],
        n_neighbors=HDBSCAN_CONFIG["umap_n_neighbors"],
        random_state=42,
        low_memory=False,
    )
    t0 = time.time()
    X_reduced = reducer.fit_transform(X)
    logger.info(
        "UMAP: %d → %d dims in %.2fs",
        X.shape[1],
        HDBSCAN_CONFIG["umap_n_components"],
        time.time() - t0,
    )
    return X_reduced


def _hdbscan_cluster(X_reduced: np.ndarray) -> np.ndarray:
    """Run HDBSCAN on UMAP-reduced embeddings.

    Points that do not belong to any dense cluster are labelled ``-1`` (noise /
    zero-day outliers). The caller is responsible for routing these.

    Args:
        X_reduced: UMAP-reduced matrix (n_samples, n_components).

    Returns:
        Integer label array of shape (n_samples,).  ``-1`` == noise.
    """
    import hdbscan as hdbscan_lib  # type: ignore[import]

    clusterer = hdbscan_lib.HDBSCAN(
        min_cluster_size=HDBSCAN_CONFIG["min_cluster_size"],
        min_samples=HDBSCAN_CONFIG["min_samples"],
        cluster_selection_method=HDBSCAN_CONFIG["cluster_selection_method"],
        prediction_data=False,
    )
    t0 = time.time()
    labels = clusterer.fit_predict(X_reduced)
    n_found = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int((labels == -1).sum())
    logger.info(
        "HDBSCAN: %d clusters found, %d noise points (%.1f%%) in %.2fs",
        n_found,
        n_noise,
        100 * n_noise / max(len(labels), 1),
        time.time() - t0,
    )
    return labels


# ---------------------------------------------------------------------------
# Main clusterer
# ---------------------------------------------------------------------------

class SemanticThematicClusterer:
    """
    Unsupervised thematic clustering engine.
    Groups customer feedback into dense semantic clusters using all-MiniLM-L6-v2
    transformer embeddings (384 dimensions) with class-based c-TF-IDF keyword extraction.

    Supports two clustering backends controlled by ``pipeline_config.CLUSTERING_MODE``:

    * ``"kmeans"`` (default) — MiniBatchKMeans, always available.
    * ``"hdbscan"`` — UMAP + HDBSCAN density clustering. Automatically discovers
      cluster count and surfaces rare zero-day clusters. Falls back to KMeans if
      ``hdbscan`` / ``umap-learn`` are not installed.
    """

    def __init__(self, n_clusters: Optional[int] = None):
        self.n_clusters = int(n_clusters) if n_clusters else int(THEME["n_clusters"])
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),
            stop_words='english',
            min_df=2
        )
        self.kmeans = MiniBatchKMeans(
            n_clusters=self.n_clusters,
            random_state=42,
            batch_size=256,
            n_init=3
        )
        self.is_fitted = False
        # Resolved lazily at fit time: the encoder may be importable now and
        # still fail to load weights later (or vice versa after a cache reset).
        self.use_transformer = TRANSFORMER_AVAILABLE

    # ------------------------------------------------------------------
    # Internal: decide and execute the clustering backend
    # ------------------------------------------------------------------

    def _cluster_embeddings(self, X: np.ndarray, texts: List[str]) -> np.ndarray:
        """Dispatch to HDBSCAN or KMeans based on CLUSTERING_MODE.

        Returns:
            Integer label array. HDBSCAN may return ``-1`` for noise points.
        """
        mode = CLUSTERING_MODE.lower()

        if mode == "hdbscan":
            if not HDBSCAN_AVAILABLE:
                logger.warning(
                    "CLUSTERING_MODE='hdbscan' requested but 'hdbscan' or 'umap-learn' "
                    "is not installed. Falling back to KMeans. "
                    "Run: pip install hdbscan umap-learn"
                )
            else:
                try:
                    X_reduced = _umap_reduce(X)
                    return _hdbscan_cluster(X_reduced)
                except Exception as exc:
                    logger.warning(
                        "HDBSCAN clustering failed (%s); falling back to KMeans.", exc
                    )

        # Default / fallback: MiniBatchKMeans
        if len(texts) < self.n_clusters:
            self.n_clusters = max(1, len(texts))
            self.kmeans.n_clusters = self.n_clusters
        return self.kmeans.fit_predict(X)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit_and_cluster(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes raw review objects and assigns cluster IDs, extracting thematic keywords.
        Uses 384-dimensional dense transformer embeddings when available.

        When CLUSTERING_MODE == "hdbscan", reviews that fall outside any dense
        cluster (HDBSCAN label -1) are collected into a synthetic
        "Uncategorised / Zero-Day" theme that is always sorted to the bottom
        of the dashboard.
        """
        texts = [r["redacted_text"] for r in reviews]

        # 1. Vector Projection: Dense Transformer Vectors or TF-IDF Fallback
        encoder = get_encoder() if TRANSFORMER_AVAILABLE else None
        self.use_transformer = encoder is not None
        if self.use_transformer:
            # Content-addressable cache key. The old key mixed only the corpus
            # length with the first/last 3 reviews, so two corpora differing in
            # the middle collided and a stale matrix was silently reused against
            # a different review list. The shared helper hashes the full ordered
            # corpus plus the model name and dimensionality.
            cache_dir = Path(__file__).resolve().parent.parent / "data" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_key = embedding_cache_key(
                texts,
                model_name=MODEL_NAME,
                dim=EMBEDDING_DIM,
                salt="reviews",
            )
            cache_file = cache_dir / f"emb_{cache_key}.npy"

            if cache_file.exists():
                X = np.load(cache_file)
            else:
                X = encoder.encode(texts, batch_size=128, show_progress_bar=False, normalize_embeddings=True)
                try:
                    np.save(cache_file, X)
                except Exception:
                    pass
        else:
            X = self.vectorizer.fit_transform(texts)

        # 2. Cluster (KMeans or HDBSCAN+UMAP, per CLUSTERING_MODE)
        cluster_labels = self._cluster_embeddings(X, texts)
        self.is_fitted = True

        # 3. Separate noise points (HDBSCAN -1) from real clusters
        noise_indices = [i for i, lbl in enumerate(cluster_labels) if lbl == -1]
        has_noise = len(noise_indices) > 0
        if has_noise:
            logger.info(
                "Zero-day pool: %d reviews could not be assigned to any dense cluster.",
                len(noise_indices),
            )

        # Identify the distinct real cluster IDs (excluding -1)
        real_cluster_ids = sorted(set(int(lbl) for lbl in cluster_labels if lbl != -1))

        # 4. Build cluster → review map
        cluster_reviews_map: Dict[int, List[Dict[str, Any]]] = {
            c_id: [] for c_id in real_cluster_ids
        }
        for idx, r in enumerate(reviews):
            c_id = int(cluster_labels[idx])
            r["cluster_id"] = c_id
            if c_id != -1:
                cluster_reviews_map[c_id].append(r)

        # 5. Extract Cluster Keywords via True Class-based c-TF-IDF
        cluster_docs = []
        valid_cluster_ids = []
        for c_id in real_cluster_ids:
            c_texts = " ".join([r["redacted_text"] for r in cluster_reviews_map[c_id]])
            if c_texts.strip():
                cluster_docs.append(c_texts)
                valid_cluster_ids.append(c_id)

        ctfidf = TfidfVectorizer(max_features=2500, stop_words='english', ngram_range=(1, 2))
        try:
            ctfidf_matrix = ctfidf.fit_transform(cluster_docs)
            c_feature_names = np.array(ctfidf.get_feature_names_out())
        except Exception:
            ctfidf_matrix = None
            c_feature_names = None

        # Corpus-wide negative rate, used as the relative-severity baseline.
        baseline_neg = corpus_negative_fraction(reviews) if corpus_negative_fraction else 0.0

        # 6. Build theme summaries for real clusters
        themes = []
        for doc_idx, c_id in enumerate(valid_cluster_ids):
            c_reviews = cluster_reviews_map[c_id]
            if not c_reviews:
                continue

            # Top keywords from c-TF-IDF
            keywords_provisional = False
            if ctfidf_matrix is not None and c_feature_names is not None:
                row = ctfidf_matrix[doc_idx].toarray()[0]
                # Only strictly positive scores are real keyword evidence; taking
                # a raw argsort slice padded small clusters with zero-score terms.
                order = np.argsort(row)[::-1]
                positive = [i for i in order if row[i] > 0][:5]
                top_keywords = c_feature_names[positive].tolist()
            else:
                # Vectorization failed. Returning a hardcoded ["general",
                # "feedback", "product"] here was indistinguishable from real
                # derived keywords in the UI, so report nothing and flag it.
                top_keywords = []
                keywords_provisional = True
                logger.warning(
                    "c-TF-IDF vectorization failed; cluster %d has no keywords "
                    "(marked keywords_provisional).",
                    c_id,
                )

            # Sentiment breakdown within cluster
            neg_count = sum(1 for r in c_reviews if r.get("sentiment_pred") == "NEGATIVE")
            neu_count = sum(1 for r in c_reviews if r.get("sentiment_pred") == "NEUTRAL")
            pos_count = sum(1 for r in c_reviews if r.get("sentiment_pred") == "POSITIVE")
            total = len(c_reviews)
            neg_ratio = (neg_count / total) if total > 0 else 0

            # Severity: single shared implementation in app.ml.severity, using
            # pipeline_config.SEVERITY plus the corpus baseline.
            if classify_severity is not None:
                severity = classify_severity(
                    neg_ratio, total, baseline_negative_fraction=baseline_neg
                )
            else:  # pragma: no cover - only if app.ml.severity is unimportable
                severity = "CRITICAL" if neg_ratio > 0.6 and total > 200 else (
                    "HIGH" if neg_ratio > 0.6 else ("MEDIUM" if neg_ratio > 0.3 else "LOW")
                )

            # Auto-title generated from top keywords
            theme_title = " & ".join(top_keywords[:2]).title() if top_keywords else f"Cluster {c_id}"

            # Assign title to individual reviews
            for r in c_reviews:
                r["theme_title"] = theme_title

            # Collect representative sample verbatims (up to 3)
            sample_verbatims = [
                {
                    "id": r["id"],
                    "rating": r["rating"],
                    "text": r["redacted_text"],
                    "raw_text": r.get("raw_text", r["redacted_text"]),
                    "batch_or_version": r.get("batch_or_version", "N/A"),
                    "sku_or_module": r.get("sku_or_module", "N/A"),
                    "highlight_span": r.get("highlight_span", None)
                }
                for r in c_reviews[:3]
            ]

            themes.append({
                "cluster_id": c_id,
                "title": theme_title,
                "keywords": top_keywords,
                "keywords_provisional": keywords_provisional,
                "keyword_source": "unavailable" if keywords_provisional else "c-tfidf",
                "severity": severity,
                "review_count": total,
                "sentiment_distribution": {
                    "NEGATIVE": neg_count,
                    "NEUTRAL": neu_count,
                    "POSITIVE": pos_count
                },
                "negative_rate": round(neg_ratio * 100, 1),
                "sample_verbatims": sample_verbatims,
                "is_zero_day": False,
            })

        # 7. Append "Uncategorised / Zero-Day" synthetic theme for HDBSCAN noise
        if has_noise:
            zero_day_reviews = [reviews[i] for i in noise_indices]
            for r in zero_day_reviews:
                r["theme_title"] = "Uncategorised / Zero-Day"

            neg_count = sum(1 for r in zero_day_reviews if r.get("sentiment_pred") == "NEGATIVE")
            neu_count = sum(1 for r in zero_day_reviews if r.get("sentiment_pred") == "NEUTRAL")
            pos_count = sum(1 for r in zero_day_reviews if r.get("sentiment_pred") == "POSITIVE")
            total = len(zero_day_reviews)
            neg_ratio = (neg_count / total) if total > 0 else 0

            themes.append({
                "cluster_id": -1,
                "title": "Uncategorised / Zero-Day",
                "keywords": [],
                "keywords_provisional": True,
                "keyword_source": "none",
                "severity": "LOW",
                "review_count": total,
                "sentiment_distribution": {
                    "NEGATIVE": neg_count,
                    "NEUTRAL": neu_count,
                    "POSITIVE": pos_count,
                },
                "negative_rate": round(neg_ratio * 100, 1),
                "sample_verbatims": [
                    {
                        "id": r["id"],
                        "rating": r["rating"],
                        "text": r["redacted_text"],
                        "raw_text": r.get("raw_text", r["redacted_text"]),
                        "batch_or_version": r.get("batch_or_version", "N/A"),
                        "sku_or_module": r.get("sku_or_module", "N/A"),
                        "highlight_span": r.get("highlight_span", None),
                    }
                    for r in zero_day_reviews[:3]
                ],
                "is_zero_day": True,
            })

        # Sort themes by urgency: most negative and high-volume first.
        # Zero-day theme is always pinned to the bottom.
        themes.sort(
            key=lambda t: (
                not t.get("is_zero_day", False),   # non-zero-day first
                t["severity"] == "CRITICAL",
                t["negative_rate"],
                t["review_count"],
            ),
            reverse=True,
        )

        return {
            "themes": themes,
            "reviews": reviews,
            "clustering_mode": CLUSTERING_MODE,
        }


clusterer = SemanticThematicClusterer()
