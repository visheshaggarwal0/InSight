# InSight: Comprehensive Project Report

## Executive Summary
InSight is an intelligent Machine Learning engine designed to solve the unstructured data bottleneck in product and support teams. By moving beyond basic keyword matching to deep semantic understanding, InSight automatically ingests raw user feedback, extracts contextual themes, predicts issue severity, and synthesizes actionable developer tickets. This document outlines the project's goals, target audience, architectural evolution, and strategic roadmap.

---

## 1. Project Vision & Goals
**The Goal:** To eliminate manual ticket triage and ensure critical user issues are never missed. 
We aim to build a pipeline that seamlessly connects the "voice of the customer" directly to the engineering workflow, transforming messy, unstructured complaints into structured, prioritized Jira tickets without human intervention.

---

## 2. The Problem Landscape
### What is the problem?
* **Volume Overload:** Product and support teams are overwhelmed by massive volumes of unstructured user feedback across reviews, surveys, and support logs.
* **Manual Bottlenecks:** Manual triage is slow, inconsistent, and highly prone to human error, meaning critical severity issues (like app crashes or payment failures) are often missed or delayed.
* **Data Blindness:** Over 80% of enterprise data is unstructured text, making it incredibly difficult to quantify emerging product issues at scale using traditional BI tools.

### Why do current options fall short?
* Traditional BI tools rely entirely on structured data.
* Legacy NLP solutions rely on rigid keyword matching, suffering from "lexical mismatch" (e.g., failing to connect "software closed" with "app crashed"). 
* Current tools stop at analysis—they build word clouds or sentiment graphs but fail to automate the actual workflow of reporting the bug to engineering.

---

## 3. Target Audience & Customer Profiles
### Who faces this problem?
* **Product Managers (PMs):** Need to understand emerging feature requests and user friction points to prioritize the roadmap.
* **Customer Support Teams:** Drowning in support tickets; they need a way to auto-route issues to the right engineering pods.
* **Business Analysts:** Need to quantify qualitative feedback to justify business decisions.

### Ideal Customer Profiles (ICPs)
* **SaaS Platforms:** Companies dealing with constant feature requests and complex bug reports.
* **D2C Brands:** E-commerce companies handling high volumes of product reviews and shipping complaints.

---

## 4. The InSight Solution
**Our idea in one line:** We are building an intelligent NLP engine that helps product teams automatically extract semantic themes, predict severity, and generate developer tickets from unstructured user feedback.

### Key Capabilities
1. **Semantic Clustering:** Groups feedback by true meaning using dense embeddings, rather than just matching exact words.
2. **Multi-Task Triage:** Simultaneously predicts user sentiment and issue severity with mathematically calibrated confidence scores.
3. **Automated Workflow:** Synthesizes grouped complaints directly into structured, actionable Jira bug reports, bridging the gap between support and engineering.

---

## 5. Technical Architecture & Engineering Narrative
Rather than over-engineering from day one, InSight was built in two phases to ensure a robust foundation.

### Phase 1: v1 Classical MVP (The Baseline)
* **Stack:** Sublinear TF-IDF, Sparse MiniBatchKMeans, Logistic Regression.
* **Pros:** Ultra-low latency (<0.5ms), zero neural dependencies.
* **Cons:** Fundamentally lacked semantic understanding (lexical mismatch).

### Phase 2: v2 Neural Engine (Current Architecture)
To solve the semantic limitations of v1, we transitioned to a state-of-the-art transformer and SLM-based architecture.
* **Embeddings:** `all-MiniLM-L6-v2` Bi-Encoder + `c-TF-IDF` for dense topic extraction.
* **Classification:** Multi-task `DeBERTa-v3` head for simultaneous sentiment and severity prediction.
* **Synthesis:** Microsoft `Phi-3-mini` Small Language Model (SLM) for generative Jira ticket creation.
* **Backend:** FastAPI (Python) backed by Azure Blob Storage.

### Engineering Optimizations
To handle the compute overhead of transformers without relying on expensive GPU instances or complex quantization, we implemented:
* **Lazy Loading & Disk Caching:** Dense embeddings for large datasets take ~35s on CPU. We built a SHA-256 keyed `.npy` disk caching layer. The backend lazily initializes domains (`ensure_initialized()`), instantly loading pre-computed embeddings and bypassing the native PyTorch inference bottleneck for known data.

---

## 6. Current Status (What we are doing)
* **Architecture Shift Complete:** Successfully migrated the core engine from v1 to v2.
* **Testing & Reliability:** Wrote and passed a comprehensive PyTest suite for all API endpoints (`/api/overview`, `/api/themes`, etc.).
* **Data Pre-computation:** Generated and cached embeddings for our primary demo domains (`tech_saas` and `d2c_cosmetics`).
* **Notebooks:** Generated production-grade Jupyter notebooks for model finetuning and calibration.

---

## 7. Roadmap & Next Steps (What we are planning)
* **Step 1: Integration:** Finalize the integration of the native DeBERTa and Phi-3 models with our optimized lazy-loading architecture.
* **Step 2: Frontend / Visualization:** Integrate the API with a React frontend or PowerBI dashboard to visualize the c-TF-IDF semantic clusters.
* **Step 3: Demo Readiness:** Ensure the working demo flawlessly ingests messy, raw user feedback and instantly outputs a structured Jira ticket on screen, relying on our pre-warmed cache for instant response times.
* **Step 4: Cloud Deployment:** Deploy the FastAPI backend to Azure Container Apps.

---

## 8. Business Impact & Feasibility
### Expected Impact
* **Efficiency:** Aiming to reduce ticket triage time by 80%.
* **Quality:** Drastically decrease time-to-resolution for high-severity issues by routing them directly to developers in a structured format.

### Feasibility
Our team possesses the required NLP domain expertise, having successfully navigated the transition from classical ML to transformers. We already have a functioning, tested FastAPI backend and have proven the ability to optimize native pipeline performance via intelligent disk caching, ensuring a highly performant hackathon deliverable.
