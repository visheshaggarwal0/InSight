# Sephora Cosmetics Dataset Exploration & Preparation Report

## 1. Executive Summary
* **Raw Archive:** `InSight_ML/data/raw/cosmetics/archive.zip` (~153.9 MB compressed, ~525 MB uncompressed).
* **Scope:** Sephora cosmetics customer reviews and linked product catalog metadata.
* **Total Raw Reviews:** 1,094,411 records across 5 partition files (`reviews_0-250.csv` to `reviews_1250-end.csv`).
* **Total Clean Reviews:** 1,092,967 records after removing missing/whitespace review comments (1,444 empty texts discarded).
* **Product Catalog:** `product_info.csv` containing 8,494 distinct products across 27 metadata attributes.
* **ML-Ready Sample:** Produced a deterministic, reproducible sample of **10,000 reviews** (`random_state=42`) saved to `InSight_ML/data/processed/cosmetics/cosmetics_10k.csv`.
* **Privacy & Compliance:** Demographic personal identifiers (`author_id`, `skin_tone`, `eye_color`, `skin_type`, `hair_color`) and row artifacts (`Unnamed: 0`) have been excluded from the processed ML sample.
* **Weak Labeling:** Implemented heuristic sentiment labeling:
  * Rating 1–2 $\rightarrow$ `negative`
  * Rating 3 $\rightarrow$ `neutral`
  * Rating 4–5 $\rightarrow$ `positive`
  * *Notice: These are heuristic weak labels for preliminary modeling, not verified human ground truth.*

---

## 2. Dataset Architecture & Partition Breakdown

| Partition File | Raw Records | Clean Reviews | Compression Ratio | Uncompressed Size |
|---|---|---|---|---|
| `reviews_0-250.csv` | 602,130 | 601,131 | 3.4x | 282.3 MB |
| `reviews_250-500.csv` | 206,725 | 206,553 | 3.4x | 100.3 MB |
| `reviews_500-750.csv` | 116,262 | 116,137 | 3.4x | 56.3 MB |
| `reviews_750-1250.csv` | 119,317 | 119,228 | 3.4x | 58.0 MB |
| `reviews_1250-end.csv` | 49,977 | 49,918 | 3.3x | 24.2 MB |
| **Total Reviews** | **1,094,411** | **1,092,967** | **3.4x** | **521.1 MB** |
| `product_info.csv` | 8,494 | 8,494 | 5.8x | 7.9 MB |

---

## 3. Product Catalog Overview (`product_info.csv`)
* **Total Products:** 8,494
* **Unique Brands:** 304
* **Top Primary Categories:**
| primary_category   |   count |
|:-------------------|--------:|
| Skincare           |    2420 |
| Makeup             |    2369 |
| Hair               |    1464 |
| Fragrance          |    1432 |
| Bath & Body        |     405 |
| Mini Size          |     288 |
* **Price Distribution (USD):**
  * Min: $3.00
  * Median: $35.00
  * Mean: $51.66
  * Max: $1900.00

---

## 4. 10k Sample Statistics & Feature Engineering

### 4.1 Rating & Weak Sentiment Breakdown
* **Rating 5:** 6,400 (64.0%)
* **Rating 4:** 1,835 (18.4%)
* **Rating 3:** 746 (7.5%)
* **Rating 2:** 479 (4.8%)
* **Rating 1:** 540 (5.4%)

**Sentiment Distribution:**
* **Positive (Ratings 4–5):** 8,235 (82.3%)
* **Neutral (Rating 3):** 746 (7.5%)
* **Negative (Ratings 1–2):** 1,019 (10.2%)

*Note on Class Imbalance:* Over 82% of reviews are positive, typical of e-commerce cosmetic platforms. When training downstream classifiers, stratified sampling or class re-weighting should be evaluated.

### 4.2 Review Text Length Statistics
* **Mean Word Count:** 61.0 words
* **Median Word Count:** 50.0 words
* **Standard Deviation:** 45.3 words
* **Min / Max:** 1 words / 633 words
* **Interquartile Range (IQR):** 25th percentile = 32 words, 75th percentile = 76 words.

### 4.3 Temporal Trend
* **Date Range:** 2008-09-11 to 2023-03-21
* Review volume grew steadily from 2008 through peak activity in 2020–2022.

### 4.4 Top Non-Stopwords / Topical Terms
The most frequent descriptive terms in customer reviews reflect product performance, sensory feel, and satisfaction:
`love` (3,832), `face` (3,216), `really` (2,630), `dry` (2,154), `great` (2,007), `feel` (1,883), `one` (1,733), `would` (1,716), `cream` (1,644), `makeup` (1,593), `moisturizer` (1,585), `also` (1,494), `feels` (1,469), `good` (1,468), `well` (1,392)

---

## 5. Artifacts Generated

1. **Processed Dataset:**
   * [`InSight_ML/data/processed/cosmetics/cosmetics_10k.csv`](file:///d:/Documents/InSight/InSight_ML/data/processed/cosmetics/cosmetics_10k.csv)
   * Size: ~4.89 MB
   * Records: 10,000 rows
   * Columns (16): `product_id`, `product_name`, `brand_name`, `price_usd`, `rating`, `is_recommended`, `helpfulness`, `total_feedback_count`, `total_pos_feedback_count`, `total_neg_feedback_count`, `submission_time`, `review_text`, `review_title`, `weak_sentiment`, `primary_category`, `secondary_category`, `tertiary_category`, `loves_count`, `word_count`.

2. **Generated Plots:**
   * [`InSight_ML/outputs/rating_and_sentiment_distribution.png`](file:///d:/Documents/InSight/InSight_ML/outputs/rating_and_sentiment_distribution.png)
   * [`InSight_ML/outputs/review_length_distribution.png`](file:///d:/Documents/InSight/InSight_ML/outputs/review_length_distribution.png)
   * [`InSight_ML/outputs/reviews_trend_over_time.png`](file:///d:/Documents/InSight/InSight_ML/outputs/reviews_trend_over_time.png)
   * [`InSight_ML/outputs/top_categories_and_brands.png`](file:///d:/Documents/InSight/InSight_ML/outputs/top_categories_and_brands.png)

3. **Exploration Notebook:**
   * [`InSight_ML/notebooks/01_cosmetics_data_exploration.ipynb`](file:///d:/Documents/InSight/InSight_ML/notebooks/01_cosmetics_data_exploration.ipynb)
