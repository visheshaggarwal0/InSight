# InSight Reproduction & Team Setup Guide

This guide describes how any team member can clone the **InSight** repository and reproduce the complete machine learning pipeline, tests, backend, and dashboard from scratch on any computer without needing private local paths or pre-existing local machine caches.

---

## 1. Prerequisites

* **Git**: Installed with command-line access (`git --version`)
* **Python**: Version `3.10` or higher (`python --version`)
* **Node.js** (Optional, for web frontend): Node `v18+` and npm (`node --version`)

---

## 2. Quickstart (3 Commands)

```bash
# 1. Clone the repository
git clone https://github.com/visheshaggarwal0/InSight.git
cd InSight

# 2. Install dependencies & verify model artifacts
pip install -r requirements.txt
python scripts/download_models.py

# 3. Run the ML pipeline
python InSight_ML/run_pipeline.py
```

---

## 3. Detailed Setup Instructions

### Step 1: Clone Repository
```bash
git clone https://github.com/visheshaggarwal0/InSight.git
cd InSight
```

### Step 2: Create and Activate Virtual Environment
It is recommended to use an isolated Python virtual environment:

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
Install all core project dependencies (Scikit-Learn, Sentence-Transformers, PyTorch, FastAPI, etc.):
```bash
pip install -r requirements.txt
```
*(If working strictly on the ML pipeline without web backend services, `pip install -r InSight_ML/requirements.txt` can also be used).*

---

## 4. Dataset Management

### A. Processed Dataset (`cosmetics_10k.csv`)
* **Status**: Included directly in the Git repository at `InSight_ML/data/processed/cosmetics/cosmetics_10k.csv` (4.88 MB).
* **Usage**: The entire ML pipeline, theme classification, complaint extraction, and regression tests operate on this verified 10,000-review dataset out of the box. No manual dataset download is required to run the pipeline.

### B. Raw Archive (`archive.zip` — 146.8 MB) — Optional
The raw Kaggle Sephora cosmetics archive is 146.79 MB and contains over 1 million unprocessed reviews across 5 chunks. Because GitHub rejects files over 100 MB, raw archives are excluded in `.gitignore` under `InSight_ML/data/raw/` to protect repository health.

**If you need to re-generate `cosmetics_10k.csv` from scratch via `01_cosmetics_data_exploration.ipynb`:**
1. Download the Kaggle Sephora dataset:
   [Sephora Products and Skincare Reviews (Kaggle)](https://www.kaggle.com/datasets/nadyinky/sephora-products-and-skincare-reviews)
2. Place the downloaded `archive.zip` at:
   `InSight_ML/data/raw/cosmetics/archive.zip`
3. Execute `InSight_ML/notebooks/01_cosmetics_data_exploration.ipynb` to re-create the reproducible 10k stratified sample.

---

## 5. Model Artifacts & Pretrained Weights

### A. Tracked Repository Artifacts (Offline by default)
All trained pipeline artifacts are tracked directly in Git under repository-relative paths:
* `InSight_ML/outputs/sentiment_baseline/sentiment_pipeline.joblib`: Trained Scikit-Learn TF-IDF + Calibrated Logistic Regression pipeline (644 KB).
* `InSight_ML/outputs/theme_detection/theme_centroids.npy`: 6 unit-normalized semantic theme centroids (9.3 KB).
* `InSight_ML/outputs/theme_detection/cluster_assignments.csv`: 10k cluster ID mappings (4.0 MB).
* `InSight_ML/outputs/theme_detection/cluster_representatives.csv`: Top keywords and provisional theme labels (8.1 KB).
* `InSight_ML/outputs/theme_detection/minilm_embeddings.npy`: Dense embeddings for the 10k reviews (15.3 MB).
* `InSight_ML/outputs/complaint_cluster_cache/`: Precomputed sentence embeddings for fast rerun caching.

### B. Pretrained Transformer (`all-MiniLM-L6-v2`)
* The pipeline uses `sentence-transformers/all-MiniLM-L6-v2` for dense sentence representations and complaint clustering.
* **Automatic First-Run Download**: On first execution, `sentence-transformers` automatically downloads the model weights (~80 MB) from Hugging Face Hub and caches them in your local user cache (`~/.cache/huggingface/hub`).
* **Pre-caching / Offline Warmup**: Run the included verification script while connected to the internet:
  ```bash
  python scripts/download_models.py
  ```
  Once cached, all pipeline stages run completely offline with no network connectivity required.

---

## 6. Verification & Test Suite

Verify that your local environment is correctly configured:

```bash
# Verify artifact integrity & warm up transformer cache
python scripts/download_models.py

# Run complete pytest test suite (110 tests)
pytest InSight_ML/tests -v
```

Expected output:
```text
======================= 109 passed, 1 skipped in ~40s =======================
```

---

## 7. Running the Pipeline

Execute the end-to-end pipeline across the 10,000 cosmetics reviews:

```bash
python InSight_ML/run_pipeline.py
```

The pipeline runs through 10 stages:
1. Schema & Data Quality Validation
2. PII Redaction
3. Offline Calibrated Sentiment Inference
4. Theme Assignment & Centroid Distance
5. Review-Level Complaint Span Extraction
6. Sentence Deconstruction & Routing (`COMPLAINT` / `RECOMMENDATION` / `PRAISE_NOISE`)
7. Sentence Complaint Clustering (`MiniBatchKMeans` + `c-TF-IDF`)
8. Review Record Assembly
9. Temporal Cohort Drift Analysis (`PSI`)
10. Highlight Span Offset Verification & Markdown Report Generation

Pipeline outputs are written to `InSight_ML/outputs/pipeline_runs/`:
* `reviews_latest.json`: Enriched review objects with PII tags, sentiment, themes, and complaint spans.
* `themes_latest.json`: Thematic summaries with severity tiers.
* `complaint_clusters_latest.json`: Sentence-level complaint cluster breakdown.
* `drift_latest.json`: PSI drift metrics across cohorts.
* `summary_latest.json`: Execution run metadata and timing breakdown.

---

## 8. Running the Web Application (Optional)

### Backend API (FastAPI)
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
Interactive API docs: `http://localhost:8000/docs`

### Frontend Dashboard (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Dashboard UI: `http://localhost:5173`

---

## 9. Environment Variables (Optional Overrides)

The pipeline is designed to work with zero configuration. However, if your environment uses custom paths, the following variables can be set:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `INSIGHT_ROOT` | Project root directory | Auto-detected from directory hierarchy |
| `INSIGHT_ARTIFACTS_DIR` | Output and artifact storage directory | `$INSIGHT_ROOT/InSight_ML/outputs` |
| `INSIGHT_DATASETS_DIR` | Dataset directory | `$INSIGHT_ROOT/InSight_ML/data` |
| `HF_HOME` | Hugging Face cache directory | Standard user cache (`~/.cache/huggingface`) |
