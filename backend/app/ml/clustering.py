import numpy as np
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans

class SemanticThematicClusterer:
    """
    Unsupervised thematic clustering engine.
    Groups customer feedback into dense semantic clusters,
    extracts representative titles via c-TF-IDF, and links back to verbatims.
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

    def fit_and_cluster(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes raw review objects and assigns cluster IDs, extracting thematic keywords.
        """
        texts = [r["redacted_text"] for r in reviews]
        if len(texts) < self.n_clusters:
            self.n_clusters = max(1, len(texts))
            self.kmeans.n_clusters = self.n_clusters

        X = self.vectorizer.fit_transform(texts)
        cluster_labels = self.kmeans.fit_predict(X)
        self.is_fitted = True

        feature_names = np.array(self.vectorizer.get_feature_names_out())
        
        # c-TF-IDF / Centroid top keywords extraction per cluster
        themes = []
        cluster_reviews_map = {i: [] for i in range(self.n_clusters)}

        for idx, r in enumerate(reviews):
            c_id = int(cluster_labels[idx])
            r["cluster_id"] = c_id
            cluster_reviews_map[c_id].append(r)

        # Build theme summaries
        for c_id in range(self.n_clusters):
            c_reviews = cluster_reviews_map[c_id]
            if not c_reviews:
                continue

            # Top keywords from centroid
            center = self.kmeans.cluster_centers_[c_id]
            top_indices = center.argsort()[::-1][:5]
            top_keywords = feature_names[top_indices].tolist()

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
                    "batch_or_version": r.get("batch_or_version", "N/A"),
                    "sku_or_module": r.get("sku_or_module", "N/A")
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
