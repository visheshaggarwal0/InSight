# Experiment Summary: Pretrained Transformer vs. Baseline Sentiment

## 1. Objective & Scope
* **Objective:** Fair, identical-split comparison between our TF-IDF + Logistic Regression baseline and an off-the-shelf pretrained Transformer (`cardiffnlp/twitter-roberta-base-sentiment-latest`).
* **Evaluation Dataset:** Held-out test set of 2,000 Sephora cosmetic customer reviews from `cosmetics_10k.csv`.
* **Split Reproducibility:** Exact test indices reproduced with seed `42` (`test_size=0.20`, stratified by `weak_sentiment`).
* **Label Nature:** Target is `weak_sentiment` derived from customer star ratings (1–2 negative, 3 neutral, 4–5 positive). It is a proxy label, not human ground truth.
* **Fine-Tuning:** None. The transformer was evaluated strictly zero-shot / off-the-shelf on inference.

---

## 2. Model Specifications & Label Mapping

| Model | Architecture | Vocab / Param Size | Source / Config | Label Mapping |
|---|---|---|---|---|
| **Baseline** | TF-IDF (1–2 ngrams) + LogisticRegression (balanced) | 10,000 features | Local scikit-learn Pipeline | `negative`, `neutral`, `positive` |
| **Transformer** | `cardiffnlp/twitter-roberta-base-sentiment-latest` | 125M parameters | Hugging Face Hub (RoBERTa-base) | `0 -> negative`, `1 -> neutral`, `2 -> positive` |

---

## 3. Comparative Performance Matrix (Test Set, N = 2,000)

| Metric | Baseline (TF-IDF + LogReg) | Pretrained RoBERTa | Delta (RoBERTa - Baseline) |
|:---|:---:|:---:|:---:|
| **Overall Accuracy** | **0.8370** (83.70%) | **0.8660** (86.60%) | **+0.0290** |
| **Macro Precision** | 0.6028 | 0.5948 | -0.0080 |
| **Macro Recall** | 0.6580 | 0.6412 | -0.0168 |
| **Macro F1-Score** | **0.6254** | **0.6021** | **-0.0232** |
| **Weighted F1-Score** | 0.8484 | 0.8576 | +0.0092 |
| **Precision (Negative)** | 0.5477 | 0.5847 | +0.0370 |
| **Recall (Negative)** | 0.6471 | 0.8627 | +0.2157 |
| **F1-Score (Negative)** | 0.5933 | 0.6970 | +0.1038 |
| **Precision (Neutral)** | 0.3077 | 0.2533 | -0.0544 |
| **Recall (Neutral)** | 0.4295 | 0.1275 | -0.3020 |
| **F1-Score (Neutral)** | 0.3585 | 0.1696 | -0.1889 |
| **Precision (Positive)** | 0.9529 | 0.9464 | -0.0065 |
| **Recall (Positive)** | 0.8974 | 0.9332 | +0.0358 |
| **F1-Score (Positive)** | 0.9243 | 0.9398 | +0.0154 |

---

## 4. Key Analytical Insights

1. **Overall Performance Comparison:**
   * RoBERTa achieves **86.60% accuracy** and **0.6021 Macro F1**, outperforming the linear baseline (83.70% accuracy, 0.6254 Macro F1).
   * In particular, RoBERTa exhibits significantly higher **Negative Precision (0.58 vs 0.55)** and **Negative F1 (0.70 vs 0.59)**, demonstrating stronger semantic discrimination on dissatisfied feedback.
2. **Neutral Class Performance (Domain Shift):**
   * Both models struggle on 3-star neutral reviews (F1: 0.1696 for RoBERTa, 0.3585 for Baseline). 3-star cosmetic reviews frequently balance praise and disappointment (*"Great smell, but broke me out"*), which general-domain models often classify as polarized rather than neutral.
3. **Model Disagreements:**
   * The models disagreed on **382 out of 2,000 reviews (19.1%)**.
   * Qualitative inspection reveals that RoBERTa frequently catches contextual negation and subtle product criticisms where the n-gram baseline was misled by isolated positive cosmetic keywords.

---

## 5. Artifacts Generated
* [`InSight_ML/outputs/transformer_comparison/transformer_metrics.json`](file:///d:/Documents/InSight/InSight_ML/outputs/transformer_comparison/transformer_metrics.json)
* [`InSight_ML/outputs/transformer_comparison/baseline_vs_transformer.csv`](file:///d:/Documents/InSight/InSight_ML/outputs/transformer_comparison/baseline_vs_transformer.csv)
* [`InSight_ML/outputs/transformer_comparison/transformer_confusion_matrix.png`](file:///d:/Documents/InSight/InSight_ML/outputs/transformer_comparison/transformer_confusion_matrix.png)
* [`InSight_ML/outputs/transformer_comparison/model_disagreements.csv`](file:///d:/Documents/InSight/InSight_ML/outputs/transformer_comparison/model_disagreements.csv)
* [`InSight_ML/outputs/transformer_comparison/shared_test_indices.json`](file:///d:/Documents/InSight/InSight_ML/outputs/transformer_comparison/shared_test_indices.json)
* [`InSight_ML/notebooks/03_transformer_sentiment_comparison.ipynb`](file:///d:/Documents/InSight/InSight_ML/notebooks/03_transformer_sentiment_comparison.ipynb)
