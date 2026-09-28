# InSight Deep Learning & Transformer Training Workflows

This directory contains production-grade Jupyter notebooks designed to run on free **Google Colab (T4 GPU)** or **Kaggle (P100 / T4 GPU)** for heavy transformer fine-tuning, calibration, and SLM generative synthesis.

---

## Notebook Catalog

| Notebook | Base Architecture | Training Objective & Technique | Target Environment | Export Target |
| :--- | :--- | :--- | :--- | :--- |
| **[`01_biencoder_contrastive_finetuning.ipynb`](01_biencoder_contrastive_finetuning.ipynb)** | `all-MiniLM-L6-v2` (384-d) | InfoNCE contrastive learning via `MultipleNegativesRankingLoss` with BM25 hard negatives | Colab T4 GPU (free) | Quantized INT8 ONNX (`<4ms` CPU latency) |
| **[`02_deberta_multitask_sentiment_severity.ipynb`](02_deberta_multitask_sentiment_severity.ipynb)** | `microsoft/deberta-v3-small` | Multi-task joint loss (Sentiment + Incident Severity) + Post-hoc Temperature / Platt Scaling | Colab T4 GPU (free) | Dual-head ONNX runtime checkpoint (`ECE < 3%`) |
| **[`03_phi3_qlora_jira_generator.ipynb`](03_phi3_qlora_jira_generator.ipynb)** | `microsoft/Phi-3-mini-4k-instruct` (3.8B) | 4-bit QLoRA (`bitsandbytes`, $r=16, \alpha=32$) for structured Jira bug ticket generation | Colab T4 GPU (`<6.5GB` VRAM) | Merged PEFT adapter / GGUF |

---

## 1. Contrastive Bi-Encoder (`01_biencoder_contrastive_finetuning.ipynb`)
- **Problem**: Out-of-the-box sentence encoders struggle with colloquial customer phrasing (e.g. distinguishing *"battery drains fast"* vs *"phone charges slowly"*).
- **Solution**: InfoNCE contrastive loss over mini-batches pushes true semantic complaint twins close together ($\cos(\theta) \to 1$) while repelling divergent complaints.
- **Serving**: Automatically exports to an INT8 dynamically-quantized ONNX model that drops directly into `backend/app/ml/clustering.py` for ultra-fast CPU inference.

## 2. Multi-Task DeBERTa & Calibration (`02_deberta_multitask_sentiment_severity.ipynb`)
- **Problem**: Standard deep neural networks are notoriously overconfident, producing 99% probability on ambiguous text.
- **Solution**: Trains a shared `deberta-v3-small` representation with two task heads (3-class Sentiment + 4-class Severity). Applies post-hoc Temperature Scaling ($z / T$) optimized via L-BFGS on validation Negative Log-Likelihood to lower Expected Calibration Error (ECE) from ~14% to under 3%.

## 3. Microsoft Phi-3 QLoRA Jira Synthesizer (`03_phi3_qlora_jira_generator.ipynb`)
- **Problem**: Engineering teams need actionable, reproducible bug tickets, not raw word clouds.
- **Solution**: Quantizes Microsoft's 3.8B parameter SLM to 4-bit NormalFloat (NF4). Fine-tunes attention projection matrices ($W_q, W_k, W_v, W_o$) with Low-Rank Adaptation. Takes cluster telemetry, sentiment skew, and customer verbatims to generate structured Markdown tickets with reproduction steps and root cause hypotheses.

---

## How to Plug Exported Artifacts into InSight
1. Run the notebook on Google Colab or Kaggle with GPU enabled (`Runtime -> Change runtime type -> T4 GPU`).
2. Download the exported `.onnx` or LoRA checkpoint from the notebook session.
3. Place exported ONNX models into `backend/models/`:
   - `backend/models/minilm_quantized.onnx`
   - `backend/models/deberta_multitask.onnx`
4. The InSight FastAPI backend detects the presence of local ONNX models automatically and accelerates inference via ONNX Runtime CPU.
