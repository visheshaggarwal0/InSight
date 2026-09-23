# InSight — Universal Product & Telemetry Review Intelligence

> **Team**: The Lookouts  
> **Challenge**: 17. 10,000 Reviews, No Time to Read Them (Feedback & Review Analyzer)  
> **Target Persona**: Product Managers, Quality Assurance Leads, Formulation & Packaging Teams, Support Operations  

---

## 🌟 Executive Summary

Modern product teams — whether scaling D2C consumer brands (like **L'Oréal**, **Swiss Beauty**, **Foxtale**, or **mCaffeine**) or shipping digital apps (like **Fintech/SaaS** platforms) — are drowning in tens of thousands of customer reviews and survey responses. Critical defect signals, bad ingredient batches, packaging leakages, and software regressions remain buried under sheer volume.

**InSight** is an enterprise-grade feedback telemetry platform that turns 10,000+ unstructured reviews into actionable engineering and product decisions in seconds.

Unlike naive LLM wrappers or static dashboards, InSight pairs:
1. **Mathematical Ground-Truth Validation** via supervised calibrated sentiment classification.
2. **Unsupervised Zero-Day Complaint Discovery** using dense semantic clustering to surface unknown defects without predefined taxonomies.
3. **100% Verbatim Traceability** connecting every metric back to anonymized customer quotes.
4. **Enterprise PII Scrubbing** protecting customer identity, payment details, phone numbers, and addresses.
5. **Statistical Temporal & Batch Drift Monitoring** utilizing Population Stability Index (PSI) to trigger automated anomaly alerts across product batches or app releases.
6. **Closed-Loop Actionability**: One-click generation of structured Jira/GitHub bug reports and Manufacturing QA Incident tickets.

---

## 🏗️ System Architecture

```
                               ┌────────────────────────────────────────────────────────┐
                               │                    Raw Ingestion                       │
                               │   • D2C Cosmetics & Consumer SKUs (Batches/Lots)       │
                               │   • Mobile / Web Apps (Release Versions/Devices)       │
                               │   • Custom User CSV / JSON Upload                      │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                                                           ▼
                               ┌────────────────────────────────────────────────────────┐
                               │           Enterprise PII Redaction Pipeline            │
                               │   Scrub order IDs, delivery addresses, phone numbers,   │
                               │   emails, customer names, payment & card patterns      │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                                ┌──────────────────────────┴────────────────────────┐
                                ▼                                                   ▼
             ┌────────────────────────────────────┐              ┌────────────────────────────────────┐
             │    Supervised Sentiment Engine     │              │    Unsupervised Thematic Engine    │
             │ • Calibrated Classifier (Pos/Neu/Neg)│            │ • Dense Embeddings (MiniLM-L6)     │
             │ • Evaluated on 1,000 Ground Truth  │              │ • HDBSCAN / K-Means Clustering     │
             │ • Confusion Matrix, F1, PR Curves  │              │ • c-TF-IDF / Topic Auto-Labeler    │
             └──────────────────┬─────────────────┘              └──────────────────┬─────────────────┘
                                │                                                   │
                                └──────────────────────────┬────────────────────────┘
                                                           │
                                                           ▼
                               ┌────────────────────────────────────────────────────────┐
                               │             Temporal & Batch Drift Engine              │
                               │   Tracks PSI across Manufacturing Lots / Formula Drops │
                               │   or Software Versions (Automated Regression Alerts)   │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                                                           ▼
                               ┌────────────────────────────────────────────────────────┐
                               │                FastAPI Asynchronous Backend            │
                               │   Endpoints: /telemetry, /themes, /drift, /eval, /jira │
                               │   + /upload/csv for custom real-time review batches    │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                                                           ▼
                               ┌────────────────────────────────────────────────────────┐
                               │              React + Vite Modern Dashboard             │
                               │  • Domain Switcher (D2C Beauty vs. Tech / App)         │
                               │  • Theme Explorer & Verbatim Drilldown Drawer          │
                               │  • Batch / Formula Drift Timeline & Anomaly Badges     │
                               │  • Model Governance Tab (Confusion Matrix & Accuracy)  │
                               │  • 1-Click Actionable Ticket / Incident Export         │
                               └────────────────────────────────────────────────────────┘
```

---

## 🎯 How InSight Fulfills Enterprise-Grade Rubric Criteria

| Rubric Criteria | InSight Implementation | Enterprise Value |
|---|---|---|
| **Traceable to Real Verbatims** | Bidirectional drilldown from any theme or metric card directly into individual customer comments with highlighted trigger spans. | Zero hallucination; every executive insight is supported by customer evidence. |
| **Validate Sentiment Accuracy** | Dedicated **Model Governance Suite** evaluating precision, recall, macro-F1, confusion matrix, and Brier calibration against 1,000 human-annotated reviews. | Transparent proof of model reliability and statistical defensibility. |
| **Redact Personal Data (PII)** | Multi-tier privacy engine masking customer names, phone numbers, delivery addresses, order numbers (`#ORD-XXXX`), and credit cards with a UI inspection toggle. | Full GDPR, CCPA, and enterprise security compliance before any data processing. |
| **Watch for Drift Over Time** | Continuous calculation of **Population Stability Index (PSI)** and sentiment velocity across product batches (D2C) or software releases (Apps). | Early warning system detecting formula defects or software regressions before they spiral. |

---

## 📂 Repository Structure

```
InSight/
├── README.md                 # System overview, quickstart, and feature guide
├── ARCHITECTURE.md           # Deep dive into ML pipelines, drift math, and schemas
├── ENTERPRISE_CRITERIA.md    # Detailed mapping against enterprise evaluation rubric
│
├── backend/                  # Asynchronous FastAPI Microservice
│   ├── requirements.txt      # Python dependencies
│   ├── app/
│   │   ├── main.py           # Application entrypoint & CORS
│   │   ├── core/
│   │   │   ├── config.py     # Application settings
│   │   │   └── pii.py        # Enterprise PII redaction pipeline
│   │   ├── ml/
│   │   │   ├── sentiment.py  # Supervised calibrated sentiment classifier
│   │   │   ├── evaluation.py # Ground truth validation & confusion matrix
│   │   │   ├── clustering.py # Unsupervised semantic theme extractor
│   │   │   └── drift.py      # Population Stability Index (PSI) engine
│   │   ├── data/
│   │   │   └── datasets.py   # D2C Beauty & Fintech App telemetry + CSV parser
│   │   └── api/
│   │       └── routes.py     # Clean REST API endpoints
│
└── frontend/                 # React + Vite + TypeScript Dashboard
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── App.tsx           # Main workspace shell & tab router
        ├── index.css         # Dark-mode design system & tokens
        ├── components/
        │   ├── DomainSwitcher.tsx        # Toggle D2C Beauty / Fintech / Upload
        │   ├── ThemeCard.tsx             # Interactive thematic cluster card
        │   ├── VerbatimDrawer.tsx        # Deep-dive review inspector
        │   ├── DriftTimeline.tsx         # Batch / release drift monitor
        │   ├── ModelGovernanceModal.tsx  # Ground-truth evaluation metrics
        │   └── TicketModal.tsx           # Jira / QA Incident report generator
        └── types/
            └── telemetry.ts              # TypeScript domain schemas
```

---

## ⚡ Quickstart Guide

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Unix/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000` with interactive Swagger docs at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The dashboard will launch at `http://localhost:5173`.

---

## 📊 Live Demo Scenarios

1. **D2C Skincare & Cosmetics ("Aura Botanicals / Swiss Beauty")**:
   - 10,000 customer reviews spanning Vitamin C Serum, Matte Tint, and Ceramide Cream.
   - Detects severe **Batch Drift** in `Batch-24C`: reformulating preservative caused skin tingling complaints.
   - Surfaces uncatalogued packaging flaw: *"Dropper pipettes glass cracking during delivery"*.
   - Redacts order numbers (`#ORD-90214`), customer phone numbers, and home addresses.

2. **Fintech / SaaS Mobile App ("NovaPay")**:
   - 10,000 app store reviews spanning versions `v2.1.0` through `v2.4.2`.
   - Flags an immediate **Critical Regression Alert**: release `v2.4.0` biometric auth failure (PSI = 0.38, well above the 0.25 danger threshold).
   - Generates an actionable Jira ticket with cited verbatims ready for Sprint Backlog.

3. **Custom Review Upload**:
   - Drag-and-drop any CSV containing review text to process PII masking, supervised sentiment, and theme clustering on the fly.
