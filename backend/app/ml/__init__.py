"""InSight ML Package (Serving & Inference).
Consolidates calibrated sentiment, semantic theme clustering, sentence intent extraction,
and temporal drift detection.
"""
from app.ml.sentiment import CalibratedSentimentClassifier
from app.ml.clustering import SemanticThematicClusterer
from app.ml.drift import TemporalDriftDetector, drift_detector
from app.ml.evaluation import ModelEvaluationHarness
from app.ml.sentence_pipeline import (
    classify_and_route_corpus,
    classify_and_route_review,
    deconstruct_sentences,
    SentenceRecord,
    RoutedPools,
    DebertaSentenceClassifier,
    LABEL_COMPLAINT,
    LABEL_RECOMMENDATION,
    LABEL_PRAISE_NOISE,
)
from app.ml.complaint_clustering import cluster_complaint_sentences, extract_ctfidf_keywords
from app.ml.theme_inference import ThemeInferenceEngine
from app.ml.complaint_extraction import extract_complaint_span

__all__ = [
    "CalibratedSentimentClassifier",
    "SemanticThematicClusterer",
    "TemporalDriftDetector",
    "drift_detector",
    "ModelEvaluationHarness",
    "classify_and_route_corpus",
    "classify_and_route_review",
    "deconstruct_sentences",
    "SentenceRecord",
    "RoutedPools",
    "DebertaSentenceClassifier",
    "LABEL_COMPLAINT",
    "LABEL_RECOMMENDATION",
    "LABEL_PRAISE_NOISE",
    "cluster_complaint_sentences",
    "extract_ctfidf_keywords",
    "ThemeInferenceEngine",
    "extract_complaint_span",
]
