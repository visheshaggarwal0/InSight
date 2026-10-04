# InSight ML — MiniLM Standalone Theme Inference Engine: Validation Report

## 1. Executive Summary & Objective

This report details the implementation and empirical validation of the standalone **MiniLM Theme Inference Engine** (`InSight_ML/theme_inference.py`).

The objective is to enable real-time, deterministic theme assignment for incoming customer reviews using the existing precomputed 6-class cluster centroids without retraining, reclustering, or modifying existing artifacts.

### Key Validation Outcomes:
* **Architecture:** Standalone, framework-independent module (`ThemeInferenceEngine`) using `sentence-transformers/all-MiniLM-L6-v2` and pre-normalized 384-dimensional centroids from `theme_centroids.npy`.
* **Latency Profile (Local CPU):**
  * One-time Model & Centroid Load: **~13.9 seconds**.
  * Per-Review Inference Latency: **~20.7 ms to 21.6 ms per review** (~48 reviews/second on CPU).
* **Deterministic Concordance:** **96.7% (29/30)** exact cluster match against original offline $K$-means assignments on sampled reviews from the 10k embedding set.
* **Generalization on Unseen Data:** Validated on **30 genuinely unseen reviews** extracted directly from `InSight_ML/data/raw/cosmetics/archive.zip` (verified absent from `cosmetics_10k.csv`), achieving 100% valid cluster IDs and finite cosine similarity scores.

---

## 2. Model Architecture & Math Formulation

```
Incoming Review Text 
       │
       ▼
[MiniLM Encoder: all-MiniLM-L6-v2]
       │  (Output: e in R^384, ||e||_2 = 1.0)
       ▼
[Matrix Dot Product: S = e · C^T]
       │  (C in R^(6 x 384), ||C_i||_2 = 1.0)
       ▼
Cosine Similarities: [s_0, s_1, s_2, s_3, s_4, s_5]
       │
       ├─► Argmax: predicted_cluster_id = argmax(S)
       ├─► Peak Similarity: cosine_similarity = max(S)
       └─► Theme Mapping: provisional_theme = PROVISIONAL_THEMES[predicted_cluster_id]
```

### Mathematical Equivalence:
Because both the review embedding vector $\mathbf{e}$ (`normalize_embeddings=True`) and the six precomputed centroid vectors $\mathbf{c}_i$ in `theme_centroids.npy` have unit Euclidean norms ($\|\mathbf{e}\|_2 = 1.0$, $\|\mathbf{c}_i\|_2 = 1.0$), the cosine similarity is computed directly via vector dot product:
$$\cos(\mathbf{e}, \mathbf{c}_i) = \frac{\mathbf{e} \cdot \mathbf{c}_i}{\|\mathbf{e}\|_2 \|\mathbf{c}_i\|_2} = \mathbf{e} \cdot \mathbf{c}_i$$
This eliminates expensive norm calculations at runtime, allowing batched matrix multiplication (`np.dot(embeddings, centroids.T)`) to execute in sub-millisecond time.

---

## 3. Empirical Test & Validation Results

The test suite (`InSight_ML/tests/test_theme_inference.py`) executed 6 comprehensive tests on local CPU (Python 3.10):

| Test Case | Description | Metric / Outcome | Status |
| :--- | :--- | :--- | :---: |
| `test_01_centroids_integrity_and_shape` | Validates centroid shape `(6, 384)` and unit norms ($\|c_i\|_2 = 1.0$). | Centroid shape: `(6, 384)`, all norms $= 1.0 \pm 10^{-5}$ | **PASSED** |
| `test_02_single_review_inference_structure` | Validates dictionary keys, score ranges, and provisional notice. | All 7 keys present; score $\in [-1, 1]$; `is_provisional=True` | **PASSED** |
| `test_03_inference_on_30_known_reviews` | Tests 30 reviews from original 10k dataset; checks concordance with KMeans. | Latency: **20.71 ms/rev**; Concordance: **96.7% (29/30)** | **PASSED** |
| `test_04_inference_on_30_genuinely_unseen_reviews` | Tests 30 novel reviews from raw archive (not in 10k set). | Latency: **21.65 ms/rev**; 100% valid finite scores | **PASSED** |
| `test_05_determinism_and_batch_consistency` | Compares repeated calls and single vs batch outputs. | Exact deterministic match across single and batch calls | **PASSED** |
| `test_06_blank_and_invalid_inputs` | Tests empty and whitespace strings. | Graceful fallback to `cluster_id = -1`, score $= 0.0$ | **PASSED** |

### Detailed Evaluation Cohorts:

#### Cohort 1: 30 Known Reviews (from original 10,000-review embedding set)
* **Sampling Method:** Random sample of 30 reviews from `InSight_ML/data/processed/cosmetics/cosmetics_10k.csv` (`random_state=42`).
* **Processing Speed:** 30 reviews encoded and classified in **0.621s** (**20.71 ms/review**).
* **Cluster Assignment Counts:**
  * Cluster 1 (*Facial Moisturizers & Dry Skin Hydration*): 12 reviews (40.0%)
  * Cluster 4 (*Fragrance, Scent & Sensory Properties*): 6 reviews (20.0%)
  * Cluster 3 (*Lip Care & Balms*): 5 reviews (16.7%)
  * Cluster 2 (*Acne, Breakouts & Skin Clearing*): 3 reviews (10.0%)
  * Cluster 5 (*Cleansers, Face Wash & Makeup Removal*): 3 reviews (10.0%)
  * Cluster 0 (*Eye Care & Dark Circles*): 1 review (3.3%)
* **Concordance with Original $K$-means Labels:** **29 out of 30 reviews (96.7%)** matched the exact cluster assigned by the original $K$-means model in `cluster_assignments.csv`. (The single boundary case had top-2 cosine similarities separated by only 0.008).

#### Cohort 2: 30 Genuinely Unseen Reviews (from raw `archive.zip`)
* **Sampling Method:** Extracted 30 non-null reviews from `reviews_1250-end.csv` inside `InSight_ML/data/raw/cosmetics/archive.zip`, verified against a set index to guarantee **zero overlap** with `cosmetics_10k.csv`.
* **Processing Speed:** 30 reviews encoded and classified in **0.650s** (**21.65 ms/review**).
* **Cluster Assignment Counts:**
  * Cluster 1 (*Facial Moisturizers & Dry Skin Hydration*): 12 reviews (40.0%)
  * Cluster 2 (*Acne, Breakouts & Skin Clearing*): 12 reviews (40.0%)
  * Cluster 4 (*Fragrance, Scent & Sensory Properties*): 5 reviews (16.7%)
  * Cluster 5 (*Cleansers, Face Wash & Makeup Removal*): 1 review (3.3%)
* **Score Distribution:** Cosine similarity scores on unseen data ranged from **0.4215 to 0.7482** (mean: 0.5841), indicating solid directional alignment with centroid directions.

---

## 4. Structured Output Contract

The engine returns standardized dictionaries ready for downstream backend ingestion:

```json
{
  "predicted_cluster_id": 0,
  "provisional_theme": "Eye Care & Dark Circles",
  "cosine_similarity": 0.7656,
  "cluster_similarities": {
    "0": 0.7656,
    "1": 0.5242,
    "2": 0.6058,
    "3": 0.4820,
    "4": 0.4147,
    "5": 0.4468
  },
  "cluster_similarity_by_theme": {
    "Eye Care & Dark Circles": 0.7656,
    "Facial Moisturizers & Dry Skin Hydration": 0.5242,
    "Acne, Breakouts & Skin Clearing Treatments": 0.6058,
    "Lip Care & Balms": 0.4820,
    "Fragrance, Scent & Sensory Properties": 0.4147,
    "Cleansers, Face Wash & Makeup Removal": 0.4468
  },
  "is_provisional": true,
  "provisional_notice": "Provisional unsupervised theme assignment based on cosine proximity to cluster centroid."
}
```

---

## 5. Critical Caveats & Non-Claims

> **Important Evaluation Disclaimer:**
> 1. **No Ground Truth Accuracy Claim:** These tests validate computational determinism, output validity, and mathematical centroid alignment. They do **not** claim business-theme accuracy, because no human-labeled ground truth labels exist for the unsupervised Sephora clusters.
> 2. **Known Cluster Noise:** As established in `05_cluster_quality_audit.ipynb`, unsupervised clusters contain mixed topics:
>    * Cluster 2 combines active acne blemishes with dark spot serums and chemical peel pads.
>    * Cluster 3 contains promotional/incentivized reviews alongside lip products due to stylistic phrasing similarity.
> 3. **Provisional Labeling:** All assignments remain provisional estimates of semantic proximity until validated by human domain reviewers.

---

## 6. Dependency & Integration Notes

* **Standalone Status:** `InSight_ML/theme_inference.py` has zero dependencies on FastAPI, Uvicorn, or the frontend.
* **Dependencies Required:** `sentence-transformers`, `torch`, `numpy`, `pandas`.
* **Runtime Recommendation:** For real-time batch processing, use the singleton instance `get_theme_engine()` to avoid reloading the ~80MB MiniLM model into memory on repeated calls.
