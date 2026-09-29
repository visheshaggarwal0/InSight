import numpy as np
from typing import Dict, Any, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline

class CalibratedSentimentClassifier:
    """
    Supervised, calibrated sentiment classifier.
    Produces well-calibrated probabilities across Positive, Neutral, and Negative classes.
    """
    CLASSES = ["NEGATIVE", "NEUTRAL", "POSITIVE"]

    @staticmethod
    def _create_pipeline() -> Pipeline:
        base_clf = LogisticRegression(max_iter=1000, C=1.5, class_weight='balanced', random_state=42)
        return Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=8000, sublinear_tf=True)),
            ('calibrated', CalibratedClassifierCV(estimator=base_clf, method='sigmoid', cv=3))
        ])

    def __init__(self):
        # High-efficiency n-gram TF-IDF pipeline with calibrated Logistic Regression (Platt scaling)
        self.pipeline = self._create_pipeline()
        self.is_fitted = False

    def fit(self, texts: List[str], labels: List[str]):
        """
        Train the calibrated classifier on labeled review samples.
        Instantiates a fresh pipeline prior to fitting to guarantee clean feature space isolation
        and atomically swaps the pipeline upon completion to prevent concurrent dimension mismatch.
        """
        new_pipeline = self._create_pipeline()
        new_pipeline.fit(texts, labels)
        self.pipeline = new_pipeline
        self.is_fitted = True

    def predict(self, texts: List[str]) -> List[str]:
        if not self.is_fitted:
            raise RuntimeError("Classifier must be trained before inference.")
        return list(self.pipeline.predict(texts))

    def predict_proba(self, texts: List[str]) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Classifier must be trained before inference.")
        return self.pipeline.predict_proba(texts)

    def analyze_single(self, text: str) -> Dict[str, Any]:
        """
        Returns sentiment label and calibrated confidence for a single review.
        """
        pred = self.pipeline.predict([text])[0]
        probs = self.pipeline.predict_proba([text])[0]
        class_idx = list(self.pipeline.classes_).index(pred)
        confidence = float(probs[class_idx])

        return {
            "sentiment": pred,
            "confidence": round(confidence, 4),
            "probabilities": {
                cls: round(float(probs[i]), 4)
                for i, cls in enumerate(self.pipeline.classes_)
            }
        }

sentiment_model = CalibratedSentimentClassifier()
