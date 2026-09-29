# InSight ML Workspace

This directory contains the machine learning assets, datasets, notebooks, and evaluation outputs for the **InSight Feedback & Review Analyzer** project.

## Directory Structure

```text
InSight_ML/
├── data/
│   ├── raw/
│   │   └── cosmetics/       # Original, immutable raw data files (e.g. archive.zip, uncompressed raw CSVs)
│   └── processed/
│       └── cosmetics/       # Cleaned, sampled, validated, and annotated datasets (e.g. cosmetics_10k.csv)
├── notebooks/               # Jupyter/Colab notebooks for exploratory data analysis (EDA), prototyping, and pipeline validation
├── models/                  # Serialized ML model artifacts, weights, vectorizers, and configuration files
├── outputs/                 # Exported visualizations, charts, metrics, and pipeline output files
├── reports/                 # Markdown exploration reports, data quality assessments, and experiment logs
└── README.md                # Overview and documentation of the InSight_ML workspace
```

## Directory Descriptions

* **`data/raw/`**: Holds raw, unmodified data files as initially acquired. This data is treated as read-only.
  * **`cosmetics/`**: Raw review files and archives specific to the cosmetics domain (e.g. Kaggle Sephora archive). Excluded from Git via `.gitignore` due to GitHub's 100 MB limit.
* **`data/processed/`**: Holds cleaned, deduplicated, sampled, and preprocessed datasets ready for analysis or training.
  * **`cosmetics/cosmetics_10k.csv`**: Verified 10,000-review dataset used by the end-to-end pipeline. Tracked directly in Git.
* **`notebooks/`**: Interactive notebooks for step-by-step exploration, baseline training, and evaluation (`01` through `06`).
* **`models/`**: Reserved directory for future model weight checkpoints or standalone formats.
* **`outputs/`**: Serialized offline artifacts and run exports:
  * **`sentiment_baseline/`**: `sentiment_pipeline.joblib` (TF-IDF + calibrated Logistic Regression) and evaluation metrics.
  * **`theme_detection/`**: `theme_centroids.npy` (6 clusters), `minilm_embeddings.npy`, `cluster_assignments.csv`, and representatives.
  * **`complaint_cluster_cache/`**: Content-addressable cache of MiniLM embeddings for extracted complaint sentences.
  * **`pipeline_runs/`**: Output JSON runs (`reviews_latest.json`, `themes_latest.json`, `complaint_clusters_latest.json`, `drift_latest.json`, `summary_latest.json`).
* **`reports/`**: Formal validation summaries and audit reports.

## Running the Pipeline

See the root [SETUP.md](../SETUP.md) for full reproduction instructions.

```bash
# 1. Verify dependencies & artifacts
python scripts/download_models.py

# 2. Run test suite
pytest InSight_ML/tests

# 3. Run end-to-end pipeline
python InSight_ML/run_pipeline.py
```

