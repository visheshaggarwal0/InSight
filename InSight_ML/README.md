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
  * **`cosmetics/`**: Raw review files and archives specific to the cosmetics domain.
* **`data/processed/`**: Holds cleaned, deduplicated, sampled, and preprocessed datasets ready for analysis or training.
  * **`cosmetics/`**: Processed and annotated cosmetics review datasets (e.g., weak-labeled samples).
* **`notebooks/`**: Interactive notebooks for step-by-step exploration, feature analysis, and weak-label validation.
* **`models/`**: Saved models, tokenizer/vectorizer states, and model metadata.
* **`outputs/`**: Generated plots, summary figures, and export tables produced by notebooks or scripts.
* **`reports/`**: Formal summaries, data quality findings, and analysis reports for project stakeholders and review.
