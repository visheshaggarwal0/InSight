import numpy as np
import logging
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans

logger = logging.getLogger(__name__)

# Try to initialize SentenceTransformer bi-encoder
TRANSFORMER_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    transformer_encoder = SentenceTransformer('all-MiniLM-L6-v2')
    TRANSFORMER_AVAILABLE = True
    logger.info("SentenceTransformer ('all-MiniLM-L6-v2') successfully initialized for dense clustering.")
except Exception as e:
    logger.warning(f"SentenceTransformer not available, falling back to TF-IDF: {e}")
    transformer_encoder = None

class SemanticThematicClusterer:
    """
    Unsupervised thematic clustering engine.
    Groups customer feedback into dense semantic clusters using all-MiniLM-L6-v2
    transformer embeddings (384 dimensions) with class-based c-TF-IDF keyword extraction.
    """
    
    def __init__(self, n_clusters: int = 6):
        self.n_clusters = n_clusters
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
        if self.use_transformer and transformer_encoder is not None:
            import hashlib
            from pathlib import Path
            
            # Content-addressable cache key based on sample texts + total count
            cache_dir = Path(__file__).resolve().parent.parent / "data" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            key_src = f"{len(texts)}_" + "_".join(texts[:3]) + "_".join(texts[-3:])
            cache_key = hashlib.sha256(key_src.encode("utf-8")).hexdigest()[:16]
            cache_file = cache_dir / f"emb_{cache_key}.npy"

            if cache_file.exists():
                X = np.load(cache_file)
            else:
                X = transformer_encoder.encode(texts, batch_size=128, show_progress_bar=False, normalize_embeddings=True)
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

        # Build theme summaries
        themes = []
        for doc_idx, c_id in enumerate(valid_cluster_ids):
            c_reviews = cluster_reviews_map[c_id]
            if not c_reviews:
                continue

            # Top keywords from c-TF-IDF
            if ctfidf_matrix is not None and c_feature_names is not None:
                row = ctfidf_matrix[doc_idx].toarray()[0]
                top_indices = row.argsort()[::-1][:5]
                top_keywords = c_feature_names[top_indices].tolist()
            else:
                top_keywords = ["general", "feedback", "product"]

            # Sentiment breakdown within cluster
            neg_count = sum(1 for r in c_reviews if r.get("sentiment_pred") == "NEGATIVE")
            neu_count = sum(1 for r in c_reviews if r.get("sentiment_pred") == "NEUTRAL")
            pos_count = sum(1 for r in c_reviews if r.get("sentiment_pred") == "POSITIVE")
            total = len(c_reviews)

            neg_ratio = (neg_count / total) if total > 0 else 0
            
            # Severity score: 1 to 5 based on negative ratio and volume
            if neg_ratio > 0.6:
                severity = "CRITICAL" if total > 200 else "HIGH"
            elif neg_ratio > 0.3:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            # Auto-title generated from top keywords
            theme_title = " & ".join(top_keywords[:2]).title()
            
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
