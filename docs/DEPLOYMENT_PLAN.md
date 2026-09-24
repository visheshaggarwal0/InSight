# InSight — Azure Cloud Deployment & Infrastructure Plan

This document defines the complete enterprise deployment strategy for **InSight** on Microsoft Azure, leveraging cost-optimized serverless primitives to operate under a strict **\$50 budget envelope** (projected total spend: **<\$2.00**).

---

## 1. Cloud Architecture Overview

```
                                      Internet
                                          │
                                          ▼
                       ┌─────────────────────────────────────┐
                       │       Azure Static Web Apps         │
                       │    (React + Vite Single Page App)   │
                       │   • Global CDN Edge Distribution    │
                       │   • Automated SSL & Custom Domain   │
                       │   • Cost: Free Tier ($0.00/month)   │
                       └──────────────────┬──────────────────┘
                                          │
                                          │ Proxies /api/* (Linked Backend)
                                          ▼
                       ┌─────────────────────────────────────┐
                       │        Azure Container Apps         │
                       │     (FastAPI ASGI Microservice)     │
                       │   • Serverless Consumption Plan     │
                       │   • Scale-to-Zero (0 replicas idle) │
                       │   • 180,000 vCPU-sec/month free     │
                       │   • Cost: ~$0.00 - $0.50/month      │
                       └──────────┬──────────────────┬───────┘
                                  │                  │
                Payload / Telemetry│                  │ Serverless API Calls
                                  ▼                  ▼
       ┌────────────────────────────┐      ┌─────────────────────────────┐
       │     Power BI Desktop /     │      │       Azure AI Studio       │
       │       Power BI Service     │      │   (Phi-3-mini-4k-instruct)  │
       │  • Live Web / OData Feed   │      │ • Pay-as-you-go Serverless  │
       │  • Direct /api/export/csv  │      │ • ~$0.15 / million tokens   │
       │  • Executive C-Suite BI    │      │ • On-Demand Jira Synthesis  │
       └────────────────────────────┘      └─────────────────────────────┘
```

---

## 2. Service Inventory & Cost Breakdown

| Component | Azure Service | SKU / Tier | Allocation / Free Grant | Monthly Cost |
|---|---|---|---|---|
| **Frontend UI** | Azure Static Web Apps | Free | Unlimited bandwidth, free SSL, custom domains | **$0.00** |
| **Backend API** | Azure Container Apps | Consumption | 180,000 vCPU-s & 360,000 GiB-s free monthly | **$0.00 – $0.40** |
| **Container Registry**| Azure Container Registry | Basic | 10 GB storage, standard webhooks | **~$0.16 / day** |
| **LLM Synthesis** | Azure AI Studio | Serverless API | Pay-as-you-go per token (Phi-3-mini) | **~$0.05 – $0.20** |
| **Storage / Blobs** | Azure Blob Storage | Standard LRS | Ingestion staging & cached telemetry | **<$0.02** |
| **Total Projected** | | | **24/7 demo-ready across hackathon** | **<$2.00** |

> [!IMPORTANT]
> **Zero GPU Footprint**: All Transformer inference (MiniLM dense embeddings, c-TF-IDF, and supervised calibration) runs on CPU via **Microsoft ONNX Runtime**. No expensive NC/NV-series GPU VMs (\$1.50–\$3.50/hr) are provisioned.

---

## 3. Step-by-Step Deployment Guide

### Prerequisites
- [Azure CLI (`az`)](https://learn.microsoft.com/cli/azure/install-azure-cli) installed and authenticated:
  ```bash
  az login
  az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
  ```
- Docker installed locally (or GitHub Actions for cloud builds).

---

### Step A: Resource Group & Budget Protection
Set up a dedicated resource group and hard budget alert to ensure your \$50 credits are never exceeded:

```bash
# 1. Create Resource Group in East US or Central US
az group create --name rg-insight-prod --location eastus

# 2. Configure a $20 hard budget alert
az consumption budget create \
  --budget-name "InSight-Safety-Budget" \
  --amount 20 \
  --time-grain Monthly \
  --start-date $(date -u +"%Y-%m-01") \
  --end-date "2027-12-31" \
  --resource-group rg-insight-prod
```

---

### Step B: Package & Deploy FastAPI Backend (Azure Container Apps)

#### 1. Create the `Dockerfile` in `backend/`
Ensure `backend/Dockerfile` is present:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for scientific packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Provision Azure Container Registry & Deploy Container App
```bash
# 1. Create Container Registry (Basic tier)
az acr create \
  --resource-group rg-insight-prod \
  --name acrinsightregistry \
  --sku Basic \
  --admin-enabled true

# 2. Build and push image to ACR directly in the cloud (no local Docker daemon required)
az acr build \
  --registry acrinsightregistry \
  --image insight-backend:v1 \
  ./backend

# 3. Create Container Apps Managed Environment
az containerapp env create \
  --name env-insight-prod \
  --resource-group rg-insight-prod \
  --location eastus

# 4. Deploy FastAPI Container with Scale-to-Zero capability
ACR_PASSWORD=$(az acr credential show --name acrinsightregistry --query "passwords[0].value" -o tsv)

az containerapp create \
  --name app-insight-api \
  --resource-group rg-insight-prod \
  --environment env-insight-prod \
  --image acrinsightregistry.azurecr.io/insight-backend:v1 \
  --target-port 8000 \
  --ingress external \
  --registry-server acrinsightregistry.azurecr.io \
  --registry-username acrinsightregistry \
  --registry-password $ACR_PASSWORD \
  --min-replicas 0 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --env-vars ENVIRONMENT=production ALLOWED_ORIGINS="*"
```

Retrieve your backend public FQDN:
```bash
BACKEND_URL=$(az containerapp show --name app-insight-api --resource-group rg-insight-prod --query "properties.configuration.ingress.fqdn" -o tsv)
echo "Backend URL: https://$BACKEND_URL"
```

---

### Step C: Deploy React Frontend (Azure Static Web Apps)

#### 1. Configure Production API Endpoint
In `frontend/src/App.tsx`, ensure API base points to `/api` or environment variable:
```typescript
const API_BASE = import.meta.env.VITE_API_URL || 'https://' + window.location.hostname.replace(/^[a-z0-9-]+/, 'app-insight-api');
```

#### 2. Provision Azure Static Web App via CLI or Portal
```bash
az staticwebapp create \
  --name swa-insight-web \
  --resource-group rg-insight-prod \
  --source https://github.com/visheshaggarwal0/InSight \
  --location eastus2 \
  --branch main \
  --app-location "frontend" \
  --output-location "dist" \
  --login-with-github
```

#### 3. Link Backend to Static Web App (Zero CORS Issues)
Azure Static Web Apps supports **Linked Backends**, routing all calls from `https://<swa-domain>/api/*` straight to your Container App without CORS:
```bash
az staticwebapp backends link \
  --name swa-insight-web \
  --resource-group rg-insight-prod \
  --backend-resource-id $(az containerapp show --name app-insight-api --resource-group rg-insight-prod --query id -o tsv) \
  --backend-region eastus
```

---

### Step D: Provision Microsoft Phi-3 on Azure AI Studio (Optional SLM Layer)

For on-demand Jira bug and QA incident generation:
1. Open **Azure AI Studio** (`https://ai.azure.com`).
2. Navigate to **Model Catalog** $\to$ Select **`Phi-3-mini-4k-instruct`**.
3. Click **Deploy** $\to$ Select **Serverless API (Pay-as-you-go)**.
4. Copy the **Target URI** and **API Key**.
5. Update Azure Container App environment variables:
   ```bash
   az containerapp update \
     --name app-insight-api \
     --resource-group rg-insight-prod \
     --set-env-vars AZURE_AI_ENDPOINT="https://<your-phi3-endpoint>.inference.ai.azure.com/v1" AZURE_AI_KEY="<your-key>"
   ```

---

## 4. Continuous Integration & Deployment (CI/CD)

The repository uses GitHub Actions (`.github/workflows/deploy.yml`):
1. **Frontend Workflow**: Triggers on `push` to `main` modifying `frontend/**`. Runs `tsc`, `vite build`, and uploads static bundle to SWA.
2. **Backend Workflow**: Triggers on `push` to `main` modifying `backend/**`. Builds container via Azure ACR task and updates ACA revision.

---

## 5. Verification & Health Monitoring

- **API Health Check**: `https://<BACKEND_URL>/health` returns `{"status": "ok"}`
- **API Swagger Documentation**: `https://<BACKEND_URL>/docs`
- **Model Governance Endpoint**: `https://<BACKEND_URL>/api/governance`
- **Live Power BI Export**: `https://<BACKEND_URL>/api/export/csv`
