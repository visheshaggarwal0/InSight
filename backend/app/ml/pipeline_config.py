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

import hashlib
import os
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _find_project_root() -> Path:
    """Locate the InSight project root directory."""
    here = Path(__file__).resolve().parent
    for candidate in [here, here.parent, here.parent.parent, here.parent.parent.parent]:
        if (candidate / "backend").is_dir() and (candidate / "data").is_dir():
            return candidate
    return here.parent.parent.parent


PROJECT_ROOT: Path = Path(os.environ.get("INSIGHT_ROOT", str(_find_project_root())))

# Configurable directory roots
_default_artifacts = PROJECT_ROOT / "outputs"
_default_datasets = PROJECT_ROOT / "data"

ARTIFACTS_ROOT: Path = Path(os.environ.get("INSIGHT_ARTIFACTS_DIR", str(_default_artifacts)))
DATASETS_ROOT: Path = Path(os.environ.get("INSIGHT_DATASETS_DIR", str(_default_datasets)))

# Offline ML artifacts (produced by notebooks, committed to repository)
ARTIFACTS = {
    "sentiment_pipeline": ARTIFACTS_ROOT / "sentiment_baseline" / "sentiment_pipeline.joblib",
    "cluster_assignments": ARTIFACTS_ROOT / "theme_detection" / "cluster_assignments.csv",
    "cluster_representatives": ARTIFACTS_ROOT / "theme_detection" / "cluster_representatives.csv",
    "theme_centroids": ARTIFACTS_ROOT / "theme_detection" / "theme_centroids.npy",
    "minilm_embeddings": ARTIFACTS_ROOT / "theme_detection" / "minilm_embeddings.npy",
}

# Primary processed datasets
DATASETS = {
    "cosmetics_10k": DATASETS_ROOT / "processed" / "cosmetics" / "cosmetics_10k.csv",
}

# Pipeline output directory
PIPELINE_OUTPUT_DIR: Path = ARTIFACTS_ROOT / "pipeline_runs"


def verify_artifacts() -> tuple[bool, dict[str, bool]]:
    """Check that all required offline ML artifacts exist on disk.

    Returns:
        (all_present, {artifact_key: is_present})
    """
    status = {name: path.is_file() for name, path in ARTIFACTS.items()}
    return all(status.values()), status

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
    # Expected MiniLM embedding width. Used to validate / warn about centroid
    # artifacts; the engine still derives the true dim from the .npy itself.
    "embedding_dim": 384,
}

# ---------------------------------------------------------------------------
# Clustering mode toggle
# ---------------------------------------------------------------------------
# "kmeans"  → MiniBatchKMeans (default, always available, requires n_clusters)
# "hdbscan" → UMAP(cosine, 12 components) + HDBSCAN density clustering.
#             Requires `hdbscan` and `umap-learn` packages.
#             Automatically discovers cluster count; surfaces zero-day clusters
#             as a special "Uncategorized" theme (cluster_id = -1).
#             Falls back to KMeans if either library is not installed.

CLUSTERING_MODE: str = "kmeans"   # change to "hdbscan" to enable density clustering

# HDBSCAN + UMAP tuning parameters (used only when CLUSTERING_MODE == "hdbscan")
HDBSCAN_CONFIG = {
    # UMAP: reduce 384-dim MiniLM space to this many components before HDBSCAN.
    # 12 components preserve ~95% of cluster structure while eliminating noise dims.
    "umap_n_components": 12,

    # UMAP metric — cosine is correct for unit-normalised MiniLM embeddings.
    "umap_metric": "cosine",

    # UMAP: number of neighbours considered per point (higher = more global structure)
    "umap_n_neighbors": 15,

    # HDBSCAN: minimum number of reviews to form a dense cluster.
    # Clusters smaller than this are assigned to the -1 zero-day pool.
    "min_cluster_size": 15,

    # HDBSCAN: minimum samples in the core of a cluster (controls noise tolerance).
    "min_samples": 5,

    # HDBSCAN: linkage method — "eom" (Excess of Mass) is the HDBSCAN default.
    "cluster_selection_method": "eom",
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

# ---------------------------------------------------------------------------
# Sentence-level pipeline (NEW — sentence deconstruction + classification)
# ---------------------------------------------------------------------------
# Controls how the redacted review text is split into sentences and how
# each sentence is classified into COMPLAINT | RECOMMENDATION | PRAISE/NOISE.

SENTENCE_PIPELINE = {
    # Minimum word count for a sentence fragment to be kept.
    # Fragments shorter than this (e.g. "Great." alone) are dropped.
    "min_word_count": 3,

    # Sentence classifier mode.
    # "heuristic"    : current provisional regex-based classifier (default)
    # "deberta_v3"   : future supervised DeBERTa-v3 model (not yet implemented)
    # "minilm_ft"    : future fine-tuned MiniLM model (not yet implemented)
    "classifier_mode": "heuristic",   # PROVISIONAL: change when labelled data exists

    # Whether to include sentence-level outputs in per-review records.
    "include_sentences_in_records": True,

    # Whether to run complaint clustering after routing.
    "run_complaint_clustering": True,
}

# ---------------------------------------------------------------------------
# Complaint cluster dashboard (NEW — sentence-level MiniLM + KMeans)
# ---------------------------------------------------------------------------
# These settings control clustering of the COMPLAINT sentence pool only.
# Independent from the review-level THEME clustering (which uses k=6 on
# full reviews). These are two separate, complementary cluster dimensions.

COMPLAINT_CLUSTERING = {
    # Target cluster count (auto-scales dynamically for corpus size)
    "n_clusters": 14,
    "adaptive_k": True,
    "min_clusters": 6,
    "max_clusters": 18,

    # MiniLM model (same as theme engine — shared singleton)
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",

    # KMeans batch size and init count
    "batch_size": 256,
    "n_init": 3,

    # c-TF-IDF: number of root-cause keywords per cluster
    "top_keywords": 8,

    # Number of verbatim sentences to surface per cluster in the dashboard (for pagination & infinite scroll)
    "n_verbatims": 100,

    # Severity thresholds (by complaint sentence count — NOT negative fraction)
    # Scaled to account for granular defect clusters across larger pools.
    "severity_thresholds": {
        "critical": 120,    # ≥ 120 complaint sentences → CRITICAL
        "high": 60,         # ≥ 60  → HIGH
        "medium": 20,       # ≥ 20  → MEDIUM; else → LOW
    },

    # Output path for the complaint cluster dashboard JSON
    "output_path": ARTIFACTS_ROOT / "pipeline_runs" / "complaint_clusters_latest.json",
}


# ---------------------------------------------------------------------------
# Shared embedding cache key (single source of truth)
# ---------------------------------------------------------------------------
# Two modules persist MiniLM embedding matrices to disk
# (complaint_clustering.embed_sentences and clustering.SemanticThematicClusterer).
# They previously each derived a key from only the first/last few texts plus the
# corpus length, so two corpora differing only in the middle produced an
# IDENTICAL key. Any edit to the complaint heuristics - or to the middle of the
# corpus - then silently reused a stale embedding matrix against a new sentence
# list, poisoning every downstream cluster with no warning.
#
# The key now covers:
#   * the FULL text of every row (order sensitive),
#   * the encoder model name (different weights => different matrix),
#   * the embedding dimensionality,
#   * an optional caller-supplied salt for extra cache partitioning.

def embedding_cache_key(
    texts: Iterable[str],
    model_name: str,
    dim: int,
    salt: str = "",
) -> str:
    """Return a content-addressed cache key for an embedding matrix.

    Args:
        texts: The exact ordered list of strings that will be encoded.
        model_name: Fully-qualified SentenceTransformer id.
        dim: Embedding dimensionality.
        salt: Optional extra discriminator (e.g. a pipeline stage tag).

    Returns:
        A 16-character hex digest. Identical (texts, model, dim, salt) always
        produce the same key; any change to any element produces a new one.
    """
    digest = hashlib.sha256()
    digest.update("\x1f".join(texts).encode("utf-8"))
    digest.update(f"|{model_name}|{int(dim)}|{salt}".encode("utf-8"))
    return digest.hexdigest()[:16]


# ---------------------------------------------------------------------------
# Explicit export surface
# ---------------------------------------------------------------------------
# The InSight_ML/pipeline_config.py backward-compatibility shim re-exports
# exactly these names, so this list is part of the public contract.

__all__ = [
    "PROJECT_ROOT",
    "ARTIFACTS_ROOT",
    "DATASETS_ROOT",
    "ARTIFACTS",
    "DATASETS",
    "PIPELINE_OUTPUT_DIR",
    "verify_artifacts",
    "embedding_cache_key",
    "SEVERITY",
    "PSI",
    "COMPLAINT_KEYWORDS",
    "SENTIMENT_CLASSIFIER",
    "THEME",
    "PROVISIONAL_THEME_NAMES",
    "SENTENCE_PIPELINE",
    "COMPLAINT_CLUSTERING",
    "CLUSTERING_MODE",
    "HDBSCAN_CONFIG",
]

