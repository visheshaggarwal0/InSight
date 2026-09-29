import numpy as np
from typing import Dict, Any, List, Optional
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
    def _create_pipeline(cv: Optional[int] = 3) -> Pipeline:
        base_clf = LogisticRegression(max_iter=1000, C=1.5, class_weight='balanced', random_state=42)
        if cv and cv >= 2:
            clf_step = ('calibrated', CalibratedClassifierCV(estimator=base_clf, method='sigmoid', cv=cv))
        else:
            clf_step = ('clf', base_clf)
        return Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=8000, sublinear_tf=True)),
            clf_step
        ])

    def __init__(self):
        # High-efficiency n-gram TF-IDF pipeline with calibrated Logistic Regression (Platt scaling)
        self.pipeline = self._create_pipeline()
        self.is_fitted = False

        # Attempt to initialize directly from pre-trained offline artifact if available
        try:
            from app.ml.pipeline_config import ARTIFACTS
            joblib_path = ARTIFACTS.get("sentiment_pipeline")
            if joblib_path and joblib_path.exists():
                import joblib
                self.pipeline = joblib.load(joblib_path)
                self.is_fitted = True
        except Exception:
            pass

    def fit(self, texts: List[str], labels: List[str]):
        """
        Train the calibrated classifier on labeled review samples.
        Instantiates a fresh pipeline prior to fitting to guarantee clean feature space isolation.
        Gracefully handles single-class edge cases and low-count datasets.
        """
        from collections import Counter
        counts = Counter(labels)
        unique_classes = list(counts.keys())

        if len(unique_classes) < 2:
            import logging
            logging.getLogger(__name__).warning(
                "Cannot train classifier: only 1 class '%s' present in training sample. Retaining current model.",
                unique_classes[0] if unique_classes else "NONE"
            )
            return

        min_class_count = min(counts.values())
        cv = 3 if min_class_count >= 3 else (2 if min_class_count >= 2 else None)

        new_pipeline = self._create_pipeline(cv=cv)
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
