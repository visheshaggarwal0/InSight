# Enterprise-Grade Evaluation & Criteria Matrix

This document provides a line-by-line verification of how **InSight** addresses each prompt requirement and enterprise differentiator from Challenge 17 (*10,000 Reviews, No Time to Read Them*).

---

## 1. Criterion 1: Make each theme traceable to real example verbatims

### The Problem in Naive Solutions
Most review analysis tools output generic bullet points (e.g., *"Users complain about customer support and crashes"*). Product managers and engineers cannot act on these because there is no proof, no context, and no way to inspect the raw user voice.

### InSight Implementation
- **Bidirectional Cluster-to-Verbatim Provenance**:
  - Every theme card in the dashboard maintains direct foreign-key references to every constituent review in that cluster.
  - Clicking any theme card opens the **Verbatim Inspector Drawer**, displaying the exact user quotes that formed the cluster.
  - Reviews display their exact metadata: timestamp, rating, SKU / module, manufacturing batch / app release, and channel.
- **Span-Level Highlighting**:
  - The UI highlights the exact sentences or keyword phrases that triggered the thematic classification.
- **Zero Hallucination Guarantee**:
  - Themes are mathematically derived from sentence embeddings and c-TF-IDF rather than free-form LLM generation without context.

---

## 2. Criterion 2: Validate sentiment accuracy against a labelled sample

### The Problem in Naive Solutions
Most hackathon projects use an unvalidated out-of-the-box sentiment library (e.g. standard VADER or TextBlob) and never measure actual accuracy or calibration, violating the explicit enterprise requirement.

### InSight Implementation
- **Held-Out Gold Standard Test Set**:
  - InSight maintains a curated, human-annotated ground-truth test sample ($N = 1,000$ reviews) with verified labels (`Positive`, `Neutral`, `Negative`).
- **Full Model Governance Suite**:
  - **Accuracy & Macro-F1**: Evaluated across all classes to guard against class-imbalance distortions.
  - **Confusion Matrix**: A live, interactive $3 \times 3$ contingency matrix in the UI displaying:
    - True Positives, False Positives, False Negatives for every sentiment tier.
  - **Precision & Recall breakdown**: Demonstrating minimal misclassification of high-severity negative complaints as positive.
  - **Probability Calibration**: Uses calibrated classifiers (Platt scaling) with Brier score computation so confidence scores represent true probabilities.
- **Auditable via REST API**:
  - The `/api/governance` endpoint outputs raw evaluation metrics, confusion matrix counts, and per-class metrics directly to the frontend.

---

## 3. Criterion 3: Redact personal data (PII)

### The Problem in Naive Solutions
Customer reviews on e-commerce sites (Amazon, Shopify, Nykaa) and app support channels frequently contain sensitive customer data: names, telephone numbers, home delivery addresses, email addresses, order IDs, and credit card snippets. Storing or feeding this data into third-party LLMs violates GDPR, CCPA, and basic data governance.

### InSight Implementation
- **Multi-Pass Regex + Contextual Redactor**:
  - **Order Tracking IDs**: Masks patterns like `#ORD-89218`, `OD8923719827`, `TRACK-9912`.
  - **Email Addresses**: Sanitizes all RFC-compliant email formats $\to$ `[REDACTED_EMAIL]`.
  - **Phone Numbers**: Catches global and local phone patterns (E.164, `+91`, US 10-digit) $\to$ `[REDACTED_PHONE]`.
  - **Credit Card Candidates**: Luhn-pattern credit card strings $\to$ `[REDACTED_PAYMENT]`.
  - **Physical Delivery Addresses**: Pincodes and street patterns $\to$ `[REDACTED_ADDRESS]`.
  - **Customer Names**: Identifies introduction and sign-off patterns $\to$ `[REDACTED_NAME]`.
- **UI Privacy Toggle**:
  - A role-based switch in the Verbatim Explorer allows users to toggle between *"Sanitized View (Default)"* and *"Restricted Raw View"* for auditing compliance.

---

## 4. Criterion 4: Watch for drift over time

### The Problem in Naive Solutions
Naive solutions present a static aggregate picture. In the real world, products change constantly: a cosmetic brand changes an emulsifier in Batch 24-C; a mobile app updates its biometric authentication in v2.4.0. Aggregate charts completely bury these critical regressions.

### InSight Implementation
- **Population Stability Index (PSI)**:
  - InSight continuously calculates the statistical distribution shift of topics and sentiment between successive product batches or software versions:
    $$\text{PSI} = \sum_{k=1}^K \left( \text{Actual}_k - \text{Expected}_k \right) \times \ln \left( \frac{\text{Actual}_k}{\text{Expected}_k} \right)$$
- **Automated Regression Thresholds**:
  - **$\text{PSI} < 0.10$**: Baseline Normal (Green).
  - **$0.10 \le \text{PSI} < 0.25$**: Moderate Drift (Amber).
  - **$\text{PSI} \ge 0.25$**: Critical Anomaly / Regression (Red).
- **Proactive Anomaly Alerts**:
  - When a release or batch breaches the $\text{PSI} \ge 0.25$ threshold, InSight generates an executive alert banner detailing which specific issue spiked (e.g., *"⚠️ Alert: Skin Tingling & Rash complaints spiked +380% in Batch-24C"*).

---

## 5. Bonus Differentiators (Why InSight Wins)

1. **Universal Cross-Industry Utility**:
   - Works seamlessly across physical D2C products (L'Oréal, Swiss Beauty, Foxtale, mCaffeine) and digital software/apps (Fintech, SaaS).
2. **Actionable Incident & Jira Generator**:
   - Closes the loop from insight to execution: click any complaint cluster to generate a structured Jira bug or Manufacturing QA Incident Report containing reproduction steps, affected batches/versions, and cited customer verbatims.
3. **Custom CSV Drag-and-Drop Ingestion**:
   - Instant processing of arbitrary review datasets without server reboots or code changes.
