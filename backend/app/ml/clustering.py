"""clustering.py
Unsupervised thematic clustering for review-level data.

Dense vectors come from all-MiniLM-L6-v2 when available (loaded LAZILY - see
get_encoder()), otherwise from a TF-IDF fallback. Cluster keywords are
class-based TF-IDF (c-TF-IDF) terms over the clusters themselves.
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
    from app.ml.pipeline_config import THEME, embedding_cache_key
except ImportError:  # pragma: no cover - InSight_ML shim import path
    from InSight_ML.pipeline_config import THEME, embedding_cache_key

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


class SemanticThematicClusterer:
    """
    Unsupervised thematic clustering engine.
    Groups customer feedback into dense semantic clusters using all-MiniLM-L6-v2
    transformer embeddings (384 dimensions) with class-based c-TF-IDF keyword extraction.
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


    def fit_and_cluster(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes raw review objects and assigns cluster IDs, extracting thematic keywords.
        Uses 384-dimensional dense transformer embeddings when available.
        """
        texts = [r["redacted_text"] for r in reviews]
        if len(texts) < self.n_clusters:
            self.n_clusters = max(1, len(texts))
            self.kmeans.n_clusters = self.n_clusters

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

        cluster_labels = self.kmeans.fit_predict(X)
        self.is_fitted = True

        # 2. Extract Cluster Keywords via True Class-based c-TF-IDF
        cluster_reviews_map = {i: [] for i in range(self.n_clusters)}
        for idx, r in enumerate(reviews):
            c_id = int(cluster_labels[idx])
            r["cluster_id"] = c_id
            cluster_reviews_map[c_id].append(r)

        # Concatenate text per cluster to compute class-based c-TF-IDF
        cluster_docs = []
        valid_cluster_ids = []
        for c_id in range(self.n_clusters):
            c_texts = " ".join([r["redacted_text"] for r in cluster_reviews_map[c_id]])
            if c_texts.strip():
                cluster_docs.append(c_texts)
                valid_cluster_ids.append(c_id)

        # Fit c-TF-IDF across class documents
        ctfidf = TfidfVectorizer(max_features=2500, stop_words='english', ngram_range=(1, 2))
        try:
            ctfidf_matrix = ctfidf.fit_transform(cluster_docs)
            c_feature_names = np.array(ctfidf.get_feature_names_out())
        except Exception:
            ctfidf_matrix = None
            c_feature_names = None

        # Corpus-wide negative rate, used as the relative-severity baseline.
        baseline_neg = corpus_negative_fraction(reviews) if corpus_negative_fraction else 0.0

        # Build theme summaries
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
            # pipeline_config.SEVERITY plus the corpus baseline. The previous
            # inline cutoffs (0.6 / 0.3 / 200) were a second, diverging set.
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
                "sample_verbatims": sample_verbatims
            })

        # Sort themes by urgency: most negative and high-volume first
        themes.sort(key=lambda t: (t["severity"] == "CRITICAL", t["negative_rate"], t["review_count"]), reverse=True)

        return {
            "themes": themes,
            "reviews": reviews
        }

clusterer = SemanticThematicClusterer()
