# InSight — Enterprise Analytics & Power BI Strategy Plan

This document defines the analytics architecture for **InSight**, with special focus on the **Microsoft Power BI Live Connector / Bridge**, star schema data modeling, automated DAX measures, and corporate executive reporting.

---

## 1. Executive Summary & Strategy

In enterprise feedback telemetry, there is a fundamental distinction between two operational personas:

```
┌────────────────────────────────────────────────────────┐
│                   Customer Reviews                     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
          ┌──────────────────────────────────┐
          │  InSight AI Telemetry Engine     │
          │  • PII Scrubbing (GDPR/CCPA)     │
          │  • Dense Semantic Clustering     │
          │  • Population Stability (PSI)    │
          │  • Platt-Calibrated Sentiment    │
          └────────────────┬─────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│  InSight React Dashboard │   │   Microsoft Power BI     │
│    (Operational Triage)  │   │   (Executive Analytics)  │
├──────────────────────────┤   ├──────────────────────────┤
│ • Product Managers       │   │ • C-Suite / VP Product   │
│ • QA Engineers           │   │ • Cross-Product Portfolio│
│ • Drill into verbatims   │   │ • Quarterly Trend Review │
│ • 1-Click Jira Tickets   │   │ • Corporate BI Blending  │
└──────────────────────────┘   └──────────────────────────┘
```

Rather than forcing complex operational triage workflows into Power BI or forcing executive KPI reporting into a custom app, **InSight acts as the intelligent cleansing & AI engine that feeds Microsoft Power BI**.

---

## 2. The Power BI Bridge & Live Connector Architecture

### 2.1 The REST / CSV Live Stream Endpoint
InSight exposes a high-performance, tabular telemetry endpoint specifically structured for Power BI's Web and OData connector:
- **Endpoint**: `GET /api/export/csv` or `GET /api/export/powerbi`
- **Output Format**: UTF-8 Comma-Separated Values (CSV) or OData JSON with ISO-8601 timestamps and sanitized strings.
- **Latency**: Sub-second streaming using streaming chunk response.

### 2.2 Star Schema Data Model

To ensure optimal performance in Power BI's VertiPaq in-memory engine, InSight models telemetry in a clean **Star Schema**:

```
                       ┌────────────────────────┐
                       │    Dim_Themes          │
                       ├────────────────────────┤
                       │ PK  Theme_ID           │
                       │     Theme_Title        │
                       │     Severity_Level     │
                       │     Keywords           │
                       └───────────┬────────────┘
                                   │ 1
                                   │
                                   │ *
┌─────────────────────────┐        │        ┌─────────────────────────┐
│     Dim_BatchRelease    │        ▼        │      Dim_ProductSKU     │
├─────────────────────────┤  ┌───────────┐  ├─────────────────────────┤
│ PK  Batch_Version       │◄─┤   Fact_   ├──► PK SKU_Code             │
│     Release_Date        │* │  Review   │ *│     Product_Name        │
│     PSI_Drift_Score     │  │ Telemetry │  │     Domain_Category     │
│     Drift_Status_Alert  │  └───────────┘  └─────────────────────────┘
└─────────────────────────┘        │ *
                                   │
                                   │ 1
                       ┌───────────▼────────────┐
                       │      Dim_Channel       │
                       ├────────────────────────┤
                       │ PK  Channel_ID         │
                       │     Channel_Name       │
                       │     Platform_Type      │
                       └────────────────────────┘
```

#### Fact Table Fields (`Fact_ReviewTelemetry`)
- `Review_ID` (String, PK)
- `Date` (DateTime)
- `Rating` (Integer: 1 to 5)
- `Calibrated_Sentiment` (String: POSITIVE, NEUTRAL, NEGATIVE)
- `Confidence_Score` (Decimal: 0.0000 to 1.0000)
- `Theme_ID` (Integer, FK)
- `Batch_Version` (String, FK)
- `SKU_Code` (String, FK)
- `Channel_ID` (String, FK)
- `Is_PII_Scrubbed` (Boolean)
- `PII_Entity_Count` (Integer)
- `Sanitized_Verbatim` (Text)
- `Extracted_Defect_Clause` (Text)

---

## 3. Essential Power BI DAX Measures

Include these pre-formulated DAX measures in the Power BI `.pbix` report:

### 1. Calibrated Sentiment Index (% Positive)
```dax
Calibrated Sentiment Index = 
DIVIDE(
    CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[Calibrated_Sentiment] = "POSITIVE"),
    COUNTROWS(Fact_ReviewTelemetry),
    0
) * 100
```

### 2. Defect Surge Rate (% Negative)
```dax
Defect Surge Rate = 
DIVIDE(
    CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[Calibrated_Sentiment] = "NEGATIVE"),
    COUNTROWS(Fact_ReviewTelemetry),
    0
) * 100
```

### 3. PII Scrub Compliance Rate
```dax
PII Redaction Rate = 
DIVIDE(
    CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[Is_PII_Scrubbed] = TRUE()),
    COUNTROWS(Fact_ReviewTelemetry),
    0
) * 100
```

### 4. Release-over-Release Negative Delta
```dax
Negative Delta MoM = 
VAR CurrentBatchNeg = [Defect Surge Rate]
VAR PreviousBatchNeg = 
    CALCULATE(
        [Defect Surge Rate],
        PREVIOUS(Dim_BatchRelease[Batch_Version])
    )
RETURN
CurrentBatchNeg - PreviousBatchNeg
```

### 5. Critical Anomaly Flag
```dax
Critical Anomaly Alert = 
IF(
    MAX(Dim_BatchRelease[PSI_Drift_Score]) >= 0.25,
    "CRITICAL REGRESSION",
    IF(MAX(Dim_BatchRelease[PSI_Drift_Score]) >= 0.10, "MODERATE DRIFT", "STABLE")
)
```

---

## 4. Power BI Dashboard Layout Specification

The Power BI report contains **three primary view tabs**:

### Page 1: Executive KPI & Health Cockpit
- **Top Ribbon Cards**:
  - `Total Reviews Ingested` (e.g., `10,000`)
  - `Net Sentiment Score` (e.g., `72% Pos`)
  - `Critical Defect Clusters` (e.g., `2 Active`)
  - `Active PSI Alerts` (e.g., `Batch-24C [PSI: 0.38]`)
- **Visuals**:
  - **Sentiment Trend Line**: Clustered 100% stacked area chart tracking Pos/Neu/Neg across manufacturing lots or releases.
  - **Rating Distribution Column Chart**: 1★ to 5★ breakdown with conditional formatting (Red for 1-2★, Green for 4-5★).
  - **Top Defect Themes by Negative Volume**: Horizontal bar chart sorted by negative review count.

### Page 2: Batch & Release Drift Inspector
- **Population Stability Index (PSI) Matrix**:
  - Displays each release lot against baseline.
  - Slicers for SKU/Module and Channel.
  - Visual conditional formatting: Green ($<0.10$), Amber ($0.10-0.25$), Red ($\ge 0.25$).
- **Surging Complaints Decomposition**: Clustered column chart showing which specific defect cluster drove the PSI spike.

### Page 3: Audit & Verbatim Explorer
- Table visual with: `Review ID`, `Rating`, `Channel`, `Sanitized Verbatim`, `Detected PII Tokens`, `Extracted Complaint Clause`.
- Interactive slicers for `Theme`, `Batch`, and `Sentiment`.

---

## 5. 5-Minute Power BI Desktop Setup (Zero Prior Experience Guide)

Follow these exact steps to load InSight telemetry into Power BI Desktop:

1. **Launch Power BI Desktop** (free download from Microsoft Store or web).
2. **Connect to InSight API**:
   - Click **Home** $\to$ **Get Data** $\to$ Select **Web**.
   - Enter your backend URL:
     - Local: `http://localhost:8000/api/export/csv`
     - Azure: `https://<your-container-app-fqdn>/api/export/csv`
   - Click **OK**.
3. **Inspect & Load Data**:
   - In the Navigator window, verify the preview table displaying all reviews, sanitized text, sentiment labels, and batches.
   - Click **Load**.
4. **Create Visuals in 3 Clicks**:
   - Drag `Calibrated_Sentiment` to Legend and `Review_ID` to Values $\to$ Select **Donut Chart**.
   - Drag `Batch_Version` to X-Axis and `Review_ID` to Y-Axis $\to$ Select **Clustered Column Chart**.
   - Drag `Theme_Title` to Category and `Review_ID` to Values $\to$ Select **Bar Chart**.
5. **Save Report**:
   - Save file as `InSight_Telemetry_Report.pbix` and bundle it with your pitch repository.
