"""pipeline_config.py
Centralized, transparent configuration for the InSight ML pipeline.

All thresholds, paths, and toggles are defined here so that:
  - Engineers can audit every decision in one place.
  - No threshold is silently embedded inside a function body.
  - Overrides can be injected at runtime (e.g. from environment variables).

IMPORTANT: These thresholds are provisional engineering choices, not
statistically validated operating points. Each constant includes an
inline comment explaining its rationale and status.
"""

from __future__ import annotations
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _find_project_root() -> Path:
    """Locate the InSight project root directory."""
    # Walk up from this file's location until we find a directory that
    # contains both InSight_ML/ and backend/
    here = Path(__file__).resolve().parent
    for candidate in [here, here.parent, here.parent.parent]:
        if (candidate / "InSight_ML").is_dir() and (candidate / "backend").is_dir():
            return candidate
    # Fallback: use the directory of this file's parent
    return here.parent


PROJECT_ROOT: Path = Path(os.environ.get("INSIGHT_ROOT", str(_find_project_root())))

# Offline ML artifacts (produced by notebooks)
ARTIFACTS = {
    "sentiment_pipeline": PROJECT_ROOT / "InSight_ML" / "outputs" / "sentiment_baseline" / "sentiment_pipeline.joblib",
    "cluster_assignments": PROJECT_ROOT / "InSight_ML" / "outputs" / "theme_detection" / "cluster_assignments.csv",
    "cluster_representatives": PROJECT_ROOT / "InSight_ML" / "outputs" / "theme_detection" / "cluster_representatives.csv",
    "theme_centroids": PROJECT_ROOT / "InSight_ML" / "outputs" / "theme_detection" / "theme_centroids.npy",
    "minilm_embeddings": PROJECT_ROOT / "InSight_ML" / "outputs" / "theme_detection" / "minilm_embeddings.npy",
}

# Primary processed datasets
DATASETS = {
    "cosmetics_10k": PROJECT_ROOT / "InSight_ML" / "data" / "processed" / "cosmetics" / "cosmetics_10k.csv",
}

# Pipeline output directory
PIPELINE_OUTPUT_DIR: Path = PROJECT_ROOT / "InSight_ML" / "outputs" / "pipeline_runs"

# ---------------------------------------------------------------------------
# Severity thresholds (PROVISIONAL – not statistically validated)
# ---------------------------------------------------------------------------
# These control how a theme cluster is labeled LOW/MEDIUM/HIGH/CRITICAL.
# They are based on industry convention (comparable to NPS tier cutoffs)
# but have NOT been validated for this specific dataset.
# Change these values here; do not bury them in individual module bodies.

SEVERITY = {
    # Fraction of reviews in a cluster that are NEGATIVE
    # to trigger each severity tier.
    # CRITICAL also requires cluster volume > SEVERITY_CRITICAL_MIN_COUNT.
    "critical_neg_fraction": 0.35,   # fraction ≥ this AND volume ≥ min → CRITICAL
    "high_neg_fraction":     0.35,   # fraction ≥ this AND volume < min → HIGH
    "medium_neg_fraction":   0.20,   # fraction ≥ this → MEDIUM; else → LOW
    "critical_min_volume":   500,    # minimum cluster size to qualify as CRITICAL
}

# ---------------------------------------------------------------------------
# PSI (Population Stability Index) thresholds (PROVISIONAL)
# ---------------------------------------------------------------------------
# Standard rule-of-thumb: PSI < 0.10 stable, 0.10-0.25 moderate, > 0.25 critical.
# These are industry defaults from credit scoring literature; they may not be
# appropriate for short-form cosmetics reviews. Treat as starting points.

PSI = {
    "moderate_threshold": 0.10,   # PSI ≥ this triggers a WARNING alert
    "critical_threshold": 0.25,   # PSI ≥ this triggers a CRITICAL_DRIFT alert
}

# ---------------------------------------------------------------------------
# Complaint extraction (PROVISIONAL – heuristic, no ground-truth validation)
# ---------------------------------------------------------------------------
# The keyword list below is the complete set used by the regex pattern.
# Adding or removing keywords here does NOT automatically retrain anything;
# it only changes the heuristic coverage.

COMPLAINT_KEYWORDS = [
    "but", "however", "except that", "except", "although",
    "unfortunately", "until",
    "cracked", "jammed", "leaked", "burning", "stinging",
    "rash", "dermatitis",
    "crash", "crashes", "freeze", "freezes",
    "failed", "fails", "limbo", "terrible", "horrible",
]

# ---------------------------------------------------------------------------
# Sentiment classifier (backend, synthetic-data training only)
# ---------------------------------------------------------------------------
SENTIMENT_CLASSIFIER = {
    "tfidf_max_features": 8000,
    "ngram_range": (1, 2),
    "logistic_C": 1.5,
    "logistic_max_iter": 1000,
    "calibration_method": "sigmoid",
    "calibration_cv": 3,
    "random_state": 42,
    # Training set size used at startup (first N reviews from synthetic corpus)
    "train_subset_size": 2000,
}

# ---------------------------------------------------------------------------
# Theme inference (MiniLM, k=6 clusters)
# ---------------------------------------------------------------------------
THEME = {
    "n_clusters": 6,
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "batch_size": 64,
}

# Map cluster IDs to provisional human-readable names.
# These were assigned based on visual inspection of cluster representatives
# (see outputs/theme_detection/audit/). They are NOT validated labels.
PROVISIONAL_THEME_NAMES = {
    0: "Eye Care & Dark Circles",
    1: "Facial Moisturizers & Dry Skin Hydration",
    2: "Acne, Breakouts & Skin Clearing Treatments",
    3: "Lip Care & Balms",
    4: "Fragrance, Scent & Sensory Properties",
    5: "Cleansers, Face Wash & Makeup Removal",
}
