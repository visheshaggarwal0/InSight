# Enterprise-Grade Evaluation & Criteria Matrix

This document provides a line-by-line verification of how **InSight** addresses each prompt requirement and enterprise differentiator from Challenge 17 (*10,000 Reviews, No Time to Read Them*).

---

## 1. Criterion 1: Make each theme traceable to real example verbatims

### The Problem in Naive Solutions
Most review analysis tools output generic bullet points (e.g., *"Users complain about customer support and crashes"*). Product managers and engineers cannot act on these because there is no proof, no context, and no way to inspect the raw user voice. Furthermore, naive tools classify entire reviews monolithically, completely missing critical defects buried in 3★ and 4★ feedback.

### InSight Implementation
- **Omni-Corpus Clause-Level Complaint Extraction**:
  - InSight does not rely on naive negative star-rating filters. It parses every review—regardless of star rating (1★ to 5★)—using contrastive discourse markers (`"but"`, `"however"`, `"except that"`) to extract exact defect spans.
  - Retains character start/end offsets (`span_start`, `span_end`) within the parent review.
- **Bidirectional Incident-to-Verbatim Provenance**:
  - Every canonical incident in the dashboard maintains direct foreign-key references to every constituent review containing that defect.
  - Clicking any incident opens the **Verbatim Inspector Drawer**, displaying the exact customer quotes.
  - Reviews display full audit metadata: timestamp, rating, SKU / module, manufacturing batch / app release, and channel.
- **Exact Span-Level Highlighting**:
  - The UI highlights the exact extracted complaint sentence inside the full customer verbatim with severity color-coding (Rose for P0/P1, Amber for P2).
- **Zero Hallucination Guarantee**:
  - Canonical incidents and titles are derived from dense embeddings (`all-MiniLM-L6-v2`) and c-TF-IDF rather than ungrounded LLM generation.

---

## 2. Criterion 2: Validate sentiment accuracy against a labelled sample

### The Problem in Naive Solutions
Most hackathon projects use an unvalidated out-of-the-box sentiment library (e.g. standard VADER or TextBlob) and never measure actual accuracy or calibration, violating the explicit enterprise requirement.

### InSight Implementation
- **Held-Out Gold Standard Test Set**:
  - InSight maintains a curated, human-annotated ground-truth test sample ($N = 1,000$ reviews) with verified labels (`Positive`, `Neutral`, `Negative`), strictly partitioned from training data.
- **Full Model Governance Suite**:
  - **Accuracy & Macro-F1**: Evaluated across all classes to guard against class-imbalance distortions.
  - **Confusion Matrix**: A live, interactive $3 \times 3$ contingency matrix in the UI displaying True Positives, False Positives, and False Negatives for every sentiment tier.
  - **Precision & Recall Breakdown**: Demonstrating minimal misclassification of high-severity negative complaints as positive.
  - **Probability Calibration**: Uses calibrated classifiers (Platt scaling) with Brier score computation so confidence scores represent true empirical probabilities.
- **Auditable via REST API**:
  - The `/api/governance` endpoint outputs raw evaluation metrics, confusion matrix counts, and per-class metrics directly to the frontend.

---

## 3. Criterion 3: Redact personal data (PII)

### The Problem in Naive Solutions
Customer reviews on e-commerce sites (Amazon, Shopify, Nykaa) and app support channels frequently contain sensitive customer data: names, telephone numbers, home delivery addresses, email addresses, order IDs, and credit card snippets. Storing or feeding this data into third-party LLMs violates GDPR, CCPA, and basic data governance.

### InSight Implementation
- **Zero-Trust Multi-Pass Redactor**:
  - **Order Tracking IDs**: Masks patterns like `#ORD-89218`, `OD8923719827`, `TRACK-9912`.
  - **Email Addresses**: Sanitizes all RFC 5322 email formats $\to$ `[REDACTED_EMAIL_hash]`.
  - **Phone Numbers**: Catches global and local phone patterns (E.164, `+91`, US 10-digit) $\to$ `[REDACTED_PHONE_hash]`.
  - **Payment Card Candidates (with Luhn Validation)**: Identifies 16-digit card strings and validates against the Luhn checksum algorithm before redaction $\to$ `[REDACTED_PAYMENT_CARD]`.
  - **Physical Delivery Addresses & Pincodes**: Pincodes and street patterns $\to$ `[REDACTED_POSTAL_CODE]`.
  - **Customer Names**: Identifies introduction and sign-off patterns $\to$ `[REDACTED_NAME]`.
- **HMAC Reversible Cryptographic Vault**:
  - Generates deterministic surrogate hashes allowing authorized compliance/safety officers to re-identify affected customers for safety recall notifications.
- **UI Privacy Toggle**:
  - A role-based switch in the Verbatim Explorer allows users to toggle between *"Sanitized View (Default)"* and *"Restricted Auditor View"*.

---

## 4. Criterion 4: Watch for drift over time

### The Problem in Naive Solutions
Naive solutions present a static aggregate picture. In the real world, products change constantly: a cosmetic brand changes an emulsifier in Batch 24-C; a mobile app updates its biometric authentication in v2.4.0. Aggregate charts completely bury these critical regressions.

### InSight Implementation
- **Population Stability Index (PSI)**:
  - Continuously calculates statistical distribution shift of topics and sentiment between successive product batches or software versions:
    $$\text{PSI} = \sum_{k=1}^K \left( \text{Actual}_k - \text{Expected}_k \right) \times \ln \left( \frac{\text{Actual}_k}{\text{Expected}_k} \right)$$
- **Automated Regression Thresholds**:
  - **$\text{PSI} < 0.10$**: Baseline Normal (Green).
  - **$0.10 \le \text{PSI} < 0.25$**: Moderate Drift (Amber).
  - **$\text{PSI} \ge 0.25$**: **Critical Anomaly / Regression** (Red).
- **Causal Attribution via Relative Risk ($RR$) & Fisher's Exact Test**:
  - Isolates the exact complaint responsible for the drift and calculates statistical significance ($p < 0.01$):
    $$RR = \frac{P(\text{Defect } C \mid \text{Target Batch})}{P(\text{Defect } C \mid \text{Baseline Batch})}$$
  - Triggers executive surge banners (e.g., *"⚠️ Alert: Skin Tingling & Rash complaints surged 4.8× in Batch-24C (p = 0.00012)"*).

---

## 5. Bonus Differentiators (Why InSight Wins)

1. **Four-Tier Operational Severity Matrix (P0 to P3)**:
   - Categorizes every defect into actionable engineering tiers:
     - **P0**: Physical harm, financial lockouts, crash on launch.
     - **P1**: Functional blocker (pump broken, biometric loop).
     - **P2**: Degradation (scent dislike, slow loading).
     - **P3**: Minor cosmetic nuance / feature request.
2. **Universal Cross-Industry Utility**:
   - Works seamlessly across physical D2C consumer goods (L'Oréal, Swiss Beauty, Foxtale) and digital software/apps (Fintech, SaaS).
3. **Actionable Incident & Jira Generator**:
   - Closes the loop from insight to execution: click any complaint cluster to generate a structured Jira bug or Manufacturing QA Incident Report containing reproduction steps, affected batches/versions, estimated customer blast radius, and cited verbatims.
4. **Custom CSV Drag-and-Drop Ingestion**:
   - Instant processing of arbitrary review datasets without server reboots or code changes.
