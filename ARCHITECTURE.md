# InSight System Architecture & Mathematical Foundations

This document details the engineering specifications, mathematical formulations, and algorithmic implementations underpinning **InSight**.

---

## 1. Dual-Track Machine Learning Architecture

A common failure mode in text analytics platforms is choosing either pure supervised classification (which fails to identify uncatalogued zero-day complaints) or pure unsupervised LLM prompting (which is slow, uncalibrated, and impossible to validate with rigorous metrics).

InSight deploys an integrated dual-track pipeline:

```
                            Customer Review Text
                                     │
                                     ▼
                      [Enterprise PII Redaction Gate]
                                     │
                  ┌──────────────────┴──────────────────┐
                  ▼                                     ▼
      [Supervised Sentiment Track]          [Unsupervised Discovery Track]
      • Dense Feature Projection            • Sentence-Transformers (MiniLM-L6)
      • Calibrated Probabilities            • Distance Metric: Cosine / Euclidean
      • Multiclass: Pos / Neu / Neg         • Density / Centroid Clustering
      • Evaluated vs. Gold Standard         • c-TF-IDF Topic Keyword Extraction
                  │                                     │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                      [Temporal & Batch Drift Engine]
                      • Population Stability Index (PSI)
                      • Sentiment Velocity & Anomaly Alerting
```

---

## 2. Supervised Sentiment Engine & Calibration

### 2.1 Problem Formulation
Let a corpus of customer reviews be $X = \{x_1, x_2, \dots, x_N\}$ where each review $x_i$ maps to a ground-truth sentiment label $y_i \in \{0: \text{Negative}, 1: \text{Neutral}, 2: \text{Positive}\}$.

To ensure the classifier provides true probabilistic confidence rather than overconfident uncalibrated logits, we train a classifier with **Platt Scaling (Calibrated Classifier CV with Sigmoid/Isotonic regression)**:

$$P(y_i = c \mid x_i) = \frac{1}{1 + \exp(A \cdot f(x_i) + B)}$$

where $f(x_i)$ is the uncalibrated model score, and parameters $A$ and $B$ are estimated via maximum likelihood on a hold-out cross-validation set.

### 2.2 Mathematical Evaluation Metrics
The classifier is continuously evaluated on a held-out gold-standard test set of $M = 1,000$ human-labeled reviews across five metrics:

1. **Accuracy**:
   $$\text{Acc} = \frac{1}{M} \sum_{i=1}^M \mathbb{I}(\hat{y}_i = y_i)$$

2. **Per-Class Precision, Recall, and Macro-F1**:
   $$\text{Precision}_c = \frac{TP_c}{TP_c + FP_c}, \quad \text{Recall}_c = \frac{TP_c}{TP_c + FN_c}$$
   $$\text{Macro-F1} = \frac{1}{|C|} \sum_{c \in C} \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c}$$

3. **Confusion Matrix**: Full $3 \times 3$ contingency matrix displaying True Positives, False Positives, and False Negatives.
4. **Brier Calibration Score**:
   $$\text{Brier} = \frac{1}{M} \sum_{i=1}^M \sum_{c \in C} (p_{ic} - y_{ic})^2$$
   A lower Brier score guarantees that when InSight reports a 90% confidence for a negative complaint, 9 out of 10 times the review is truly negative.

---

## 3. Unsupervised Thematic Clustering & Discovery

### 3.1 Dense Embedding Representation
Each review text is encoded into a 384-dimensional dense semantic embedding space using `all-MiniLM-L6-v2`:
$$\mathbf{e}_i = \text{Embed}(x_i) \in \mathbb{R}^{384}, \quad \|\mathbf{e}_i\|_2 = 1$$

Cosine similarity captures semantic equivalence regardless of specific vocabulary:
$$\text{Sim}(x_i, x_j) = \mathbf{e}_i \cdot \mathbf{e}_j$$

### 3.2 Dynamic Topic Grouping
Reviews are clustered into dense semantic neighborhoods representing specific issues (e.g., *"cap leakage during courier transit"*, *"formula stinging around eye contour"*, *"biometric auth timeout on Android 14"*).

### 3.3 Class-based TF-IDF (c-TF-IDF) Theme Extraction
To label clusters with human-interpretable technical phrases without hallucinating external facts, we treat each cluster $k$ as a single composite document and calculate **Class-based TF-IDF**:

$$W_{t, c} = \text{tf}_{t, c} \times \log \left( 1 + \frac{A}{f_t} \right)$$

where:
- $\text{tf}_{t, c}$ is the frequency of word $t$ in cluster $c$.
- $f_t$ is the overall frequency of word $t$ across all clusters.
- $A$ is the average number of words per cluster.

The top-ranked n-grams form the cluster title and salient key phrases.

---

## 4. Population Stability Index (PSI) & Drift Detection

### 4.1 Concept Drift Formulation
In production systems, complaints drift when:
- A new product formulation or manufacturing lot is shipped (e.g., D2C cosmetics `Batch-24A` vs `Batch-24C`).
- A software update is released (e.g., `v2.3.0` vs `v2.4.0`).

To detect statistically significant divergence without manual threshold tuning, InSight calculates the **Population Stability Index (PSI)** between a baseline period/batch $B$ and a target period/batch $T$:

$$\text{PSI} = \sum_{k=1}^K \left( P(T_k) - P(B_k) \right) \times \ln \left( \frac{P(T_k)}{P(B_k)} \right)$$

where:
- $K$ is the number of categorical theme buckets or sentiment bins.
- $P(B_k)$ is the proportion of total feedback belonging to bucket $k$ in the baseline batch.
- $P(T_k)$ is the proportion belonging to bucket $k$ in the new batch.

### 4.2 Standard Enterprise PSI Thresholds
- **$\text{PSI} < 0.10$**: Stable. Negligible distribution shift; normal operations.
- **$0.10 \le \text{PSI} < 0.25$**: Moderate Drift. Warn QA/Engineering to monitor topic movements.
- **$\text{PSI} \ge 0.25$**: **Significant / Critical Drift**. Triggers automated regression alerts, surfacing the specific cluster responsible for the divergence.

---

## 5. Enterprise PII Redaction Pipeline

Customer feedback routinely leaks sensitive personal information. InSight implements a multi-pass redaction filter before reviews hit analytics or storage:

```
Raw Customer Feedback
         │
         ├─► Regex Pass 1: Order IDs / Tracking (`#ORD-\d+`, `\bOD\d{8,}\b`)
         ├─► Regex Pass 2: Payment / Credit Card numbers (Luhn candidate strings)
         ├─► Regex Pass 3: Email Addresses (`\b[\w\.-]+@[\w\.-]+\.\w+\b`)
         ├─► Regex Pass 4: Phone Numbers (E.164, Indian +91, US formats)
         ├─► Regex Pass 5: Street Addresses & Pincodes
         └─► Entity Pass 6: Customer Names via Contextual Patterns ("My name is X", "Contacted support: Y")
         │
         ▼
Sanitized / Scrubbed Verbatim (with [REDACTED_EMAIL], [ORDER_ID_MASKED], etc.)
```

The UI provides a verified toggle allowing security-cleared personnel to audit redactions side-by-side.

---

## 6. Flexible Domain Schema

InSight unifies physical consumer goods and digital apps under a common telemetry schema:

```typescript
interface ReviewTelemetry {
  id: string;
  timestamp: string;          // ISO 8601
  domain: 'd2c_cosmetics' | 'tech_saas' | 'custom';
  product_name: string;       // e.g. "C-Glow 15% Serum" or "NovaPay Mobile"
  sku_or_module: string;      // e.g. "SKU-SER-01" or "Auth & Biometrics"
  batch_or_version: string;   // e.g. "Batch-24C" or "v2.4.0"
  channel: string;            // e.g. "Direct Website", "Nykaa", "App Store"
  raw_text: string;
  redacted_text: string;
  pii_detected: string[];     // ['EMAIL', 'ORDER_ID']
  rating: number;             // 1 to 5
  sentiment_pred: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
  sentiment_confidence: number; // 0.0 to 1.0
  cluster_id: number;
  theme_title: string;
}
```
