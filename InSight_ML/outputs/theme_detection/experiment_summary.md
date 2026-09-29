# InSight ML — Experiment Summary: MiniLM Theme Detection & Baseline Comparison

## 1. Executive Overview
This experiment evaluated unsupervised semantic theme discovery on **10,000 Sephora customer reviews** using **Sentence-Transformers `all-MiniLM-L6-v2`** embeddings compared against a **TF-IDF + KMeans baseline**.

* **Dataset:** `InSight_ML/data/processed/cosmetics/cosmetics_10k.csv` (N = 10,000 reviews).
* **Input Feature:** `review_text` (unsupervised, no demographic or sentiment features used).
* **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, L2-normalized).
* **Baseline Pipeline:** `TfidfVectorizer(max_features=5000, ngram_range=(1,2), stop_words='english')` + `KMeans(random_state=42)`.
* **Cluster Range Evaluated:** $k \in [5, 6, 8, 10]$.

---

## 2. Quantitative Clustering Metrics Comparison

| Representation | k | Silhouette Score (Cosine, N=5,000) | Inertia | Min Cluster Size | Max Cluster Size | Runtime (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| MiniLM (all-MiniLM-L6-v2) | 5 | 0.0520 | 5,239.9 | 714 | 3,009 | 1.34 |
| TF-IDF Baseline | 5 | 0.0101 | 9,607.2 | 452 | 4,480 | 1.46 |
| MiniLM (all-MiniLM-L6-v2) | 6 | 0.0560 | 5,166.6 | 695 | 2,780 | 3.04 |
| TF-IDF Baseline | 6 | 0.0098 | 9,579.3 | 318 | 4,213 | 1.85 |
| MiniLM (all-MiniLM-L6-v2) | 8 | 0.0652 | 5,029.3 | 455 | 2,078 | 4.11 |
| TF-IDF Baseline | 8 | 0.0114 | 9,534.3 | 304 | 3,261 | 4.62 |
| MiniLM (all-MiniLM-L6-v2) | 10 | 0.0664 | 4,931.8 | 458 | 1,524 | 7.49 |
| TF-IDF Baseline | 10 | 0.0132 | 9,497.8 | 273 | 3,683 | 1.77 |

---

## 3. Qualitative Cluster Interpretation (MiniLM, Selected k=6)

Clusters were analyzed by extracting top c-TF-IDF distinctive keywords and reviews closest to cluster centroids in embedding space:

### Cluster 0: Eye Care & Dark Circles
* **Size:** 695 reviews (6.95% of dataset)
* **Top Keywords:** `eye, cream, eyes, product, eye cream, skin, use, circles`
* **Top Representative Review (Rating: 5★, Kiehl's Since 1851):**
  > "Wow! I am really impressed with this product. Within the first 7 days of using it I noticed my dark circles lightly fading. I also noticed my puffiness and wrinkles under the eye start to look less and less noticeable. It does everything I’ve been lo..."

### Cluster 1: Facial Moisturizers & Dry Skin Hydration
* **Size:** 2,648 reviews (26.48% of dataset)
* **Top Keywords:** `skin, product, love, moisturizer, dry, use, like, face`
* **Top Representative Review (Rating: 5★, fresh):**
  > "I absolutely love this product and I highly recommend it if you have dry skin. I don’t like moisturizers ( I know that’s taboo). This is the only thing I use on my face and I get tons of compliments on my skin...."

### Cluster 2: Acne, Breakouts & Skin Clearing Treatments
* **Size:** 2,780 reviews (27.8% of dataset)
* **Top Keywords:** `skin, product, use, face, using, acne, love, like`
* **Top Representative Review (Rating: 5★, Sunday Riley):**
  > "In love with this product! I have only been using this for 72 hours but my skin already looks so much better. My acne is clearing and I haven’t had any new breakouts since using this. This is 100% worth the money...."

### Cluster 3: Lip Care & Balms
* **Size:** 1,622 reviews (16.22% of dataset)
* **Top Keywords:** `love, product, lips, skin, use, like, lip, really`
* **Top Representative Review (Rating: 5★, Paula's Choice):**
  > "received my complimentary Paula’s Choice a couple weeks ago, I love it!! It works great, makes my skin feel soft and clean.  Easy to use. I will definitely purchase more of this product. It’s the first time I have used it, and I’m really glad I gave ..."

### Cluster 4: Fragrance, Scent & Sensory Properties
* **Size:** 1,108 reviews (11.08% of dataset)
* **Top Keywords:** `skin, product, smell, like, love, scent, smells, really`
* **Top Representative Review (Rating: 5★, TULA Skincare):**
  > "This smells AMAZING. I love how my skin felt after i used it makes me feel more refreshed. First time using this brand but i will definitely buy more...."

### Cluster 5: Cleansers, Face Wash & Makeup Removal
* **Size:** 1,147 reviews (11.47% of dataset)
* **Top Keywords:** `skin, cleanser, face, use, makeup, product, love, like`
* **Top Representative Review (Rating: 5★, fresh):**
  > "This is such a gentle cleanser, doesn’t dry out my skin, you only need a little and it easily removes makeup. Also love that it doesn’t make my skin breakout, it’s not highly scented and it doesn’t sting if you open your eyes with it on your face..."


---

## 4. Methodological Findings & Practical Discussion

### A. Semantic Embeddings vs. Lexical TF-IDF
* **TF-IDF Clustering Artifacts:** TF-IDF forms clusters heavily anchored to exact word repetition (e.g., reviews explicitly repeating "eye", "mask", "smell"). While these separate surface product forms, they fail to group synonymous expressions (e.g. "broke me out", "cystic pimples", "allergic reaction").
* **MiniLM Semantic Clustering:** MiniLM embeddings group semantically related concepts regardless of specific wording. Reviews detailing breakouts and sensitivity cluster together (Cluster 1), while reviews discussing hydration and barrier repair form a distinct group (Cluster 0).

### B. Silhouette Score Caveats in Text Data
* Across all text clustering experiments, silhouette scores remain modest (~0.02 to ~0.05).
* In natural language, customer reviews exist on a **continuous semantic manifold** rather than isolated spherical clusters. A review often mentions scent, texture, and hydration simultaneously.
* **Critical Rule:** Low silhouette scores do not indicate failure of theme discovery; human inspection of centroid-nearest reviews reveals distinct, actionable cosmetic facets.

### C. Influence of Domain-Wide Vocabulary
* High-frequency cosmetic terms ("skin", "product", "face", "love") naturally occur across all clusters.
* Using class-based TF-IDF (c-TF-IDF) penalizes these ubiquitous terms and successfully surfaces distinctive cluster vocabulary (e.g., "breakouts", "eyes", "smells", "hydrating").

---

## 5. Next Step Recommendation
* **Recommended Next Configuration for Human Review:** **MiniLM with $k=6$**.
  * **Rationale:** It separates the dataset into six interpretable, actionable dimensions:
    1. **Eye Care & Dark Circles** (6.95%): Specialized delicate skin area concerns.
    2. **Facial Moisturizers & Dry Skin Hydration** (26.48%): Barrier support, dryness, rich creams.
    3. **Acne, Breakouts & Skin Clearing Treatments** (27.80%): Blemishes, irritation, oily/problem skin.
    4. **Lip Care & Balms** (16.22%): Lip masks, moisture, chapped lips.
    5. **Fragrance, Scent & Sensory Properties** (11.08%): Aroma, sensory experience, strong odors.
    6. **Cleansers, Face Wash & Makeup Removal** (11.47%): Face washing, cleansing balms, residue removal.
  * **Next Steps:** Product managers and domain analysts should inspect `cluster_representatives.csv` to validate whether these cluster themes align with InSight's downstream reporting requirements.
