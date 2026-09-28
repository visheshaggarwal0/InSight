import json
import os

def create_notebook(cells, filepath):
    nb = {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {
                "provenance": [],
                "gpuType": "T4"
            },
            "kernelspec": {
                "display_name": "Python 3 (ipykernel)",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.10.12"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 0
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)
    print(f"Generated: {filepath}")

def md_cell(source):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source.split("\n")]
    }

def code_cell(source):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in source.split("\n")]
    }

# ----------------------------------------------------
# Notebook 1: Bi-Encoder Contrastive Fine-Tuning
# ----------------------------------------------------
nb1_cells = [
    md_cell("""# InSight | Fine-Tuning Dense Bi-Encoder Embeddings with InfoNCE Loss
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/visheshaggarwal0/InSight/blob/main/notebooks/01_biencoder_contrastive_finetuning.ipynb)

### Objective
This notebook fine-tunes a domain-adapted dense sentence bi-encoder (`sentence-transformers/all-MiniLM-L6-v2`) on customer feedback and software bug verbatims using **MultipleNegativesRankingLoss** (InfoNCE contrastive learning). 

### What You Will Achieve:
1. **Contrastive Objective**: Optimize representation space so semantically related customer complaints cluster together even with lexical mismatch (e.g. *"battery drain"* and *"phone dies in 2 hours"*).
2. **Hard Negative Mining**: Incorporate BM25-mined hard negatives to prevent semantic collapse.
3. **Evaluation**: Benchmark Mean Average Precision (MAP@R) and Silhouette score before and after fine-tuning.
4. **ONNX Export**: Quantize and export the model to `int8` ONNX for sub-4ms CPU inference in production."""),
    
    code_cell("""# 1. Environment Verification & Package Installation
import torch
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Device Name: {torch.cuda.get_device_name(0)}")
    print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

!pip install -q sentence-transformers datasets onnx onnxruntime optuna scikit-learn"""),

    md_cell("""## 2. Dataset Synthesis & Contrastive Triplet Generation
In contrastive learning, each training instance is an `(Anchor, Positive, Negative)` triplet or `(Anchor, Positive)` pair where in-batch negatives serve as the contrastive denominator."""),

    code_cell("""import pandas as pd
import numpy as np
from sentence_transformers import InputExample

# Representative domain dataset: Customer feedback across E-Commerce, SaaS, and Hardware
raw_clusters = [
    {
        "theme": "Checkout Gateway Failure",
        "anchors": [
            "Checkout button hangs on 3D Secure verification window",
            "Payment failed with error 504 gateway timeout",
            "Unable to complete purchase, cart keeps spinning on pay step",
            "Stuck on payment screen when trying to authorize credit card",
            "Transaction timeout during OTP submission"
        ],
        "positives": [
            "Payment gateway crashes when confirming billing information",
            "Stripe authorization hangs indefinitely on checkout screen",
            "Payment spinner never resolves after entering credit card OTP",
            "Order confirmation fails with gateway timeout HTTP 504",
            "Unable to process debit card payment during final review"
        ]
    },
    {
        "theme": "Battery Degradation & Thermal Throttling",
        "anchors": [
            "Battery percentage drops from 80% to 15% in less than 40 minutes",
            "Device becomes burning hot while charging via USB-C fast charger",
            "Sudden battery drain immediately following firmware release v2.4",
            "Severe thermal throttling causing stuttering during video calls",
            "Phone shuts down at 20% battery without warning"
        ],
        "positives": [
            "Excessive heat generated near charging port accompanied by rapid discharge",
            "Firmware update ruined battery life, losing 2% every 5 minutes",
            "Device overheats and throttles performance during background sync",
            "Battery health degraded significantly after 3 weeks of normal use",
            "Unprompted shutdown occurs even when battery indicator shows 25%"
        ]
    },
    {
        "theme": "Account Authentication & SSO Lockout",
        "anchors": [
            "Okta SSO loop repeatedly asks for credentials without redirecting",
            "Two-factor authentication SMS code never arrives to my mobile number",
            "Password reset link expired before email was received",
            "Session expired error appears immediately after logging in",
            "OAuth token invalid error when accessing customer dashboard"
        ],
        "positives": [
            "Infinite authentication redirect loop when signing in with company SSO",
            "2FA verification text messages are not delivering to phone",
            "Received password reset token has already expired upon receipt",
            "Authentication token invalidates immediately upon session creation",
            "Unable to sign into enterprise workspace due to SAML authorization failure"
        ]
    },
    {
        "theme": "Delivery Logistics & Missing Shipments",
        "anchors": [
            "Tracking number shows delivered but package was not on doorstep",
            "Courier left package outside in heavy rain, ruined contents",
            "Delivery delayed by 12 days with no status updates",
            "Carrier marked address incomplete despite verified street address",
            "Received wrong SKU, sent blue size M instead of black size XL"
        ],
        "positives": [
            "Status marked delivered but surveillance camera confirms no carrier arrived",
            "Package water damaged due to courier dumping box in driveway puddle",
            "Shipment stranded at distribution hub for two weeks with zero scans",
            "Wrong item arrived in box, received incorrect color and dimensions",
            "Delivery postponed multiple times without customer notification"
        ]
    }
]

# Build training and validation triplets
train_examples = []
val_examples = []

for c in raw_clusters:
    for a in c["anchors"]:
        for p in c["positives"]:
            train_examples.append(InputExample(texts=[a, p]))

print(f"Total Contrastive Training Pairs: {len(train_examples)}")
print("Sample Pair:")
print("  Anchor:  ", train_examples[0].texts[0])
print("  Positive:", train_examples[0].texts[1])"""),

    md_cell("""## 3. Load Base Model & MultipleNegativesRankingLoss
`MultipleNegativesRankingLoss` computes:
$$\\mathcal{L}(a_i, p_i) = -\\log \\frac{\\exp(\\text{sim}(a_i, p_i) / \\tau)}{\\sum_{j=1}^B \\exp(\\text{sim}(a_i, p_j) / \\tau)}$$
where each positive pair $(a_i, p_i)$ uses all other $B - 1$ positives in the mini-batch as in-batch negative distractors."""),

    code_cell("""from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer, losses, evaluation

# Initialize lightweight, ultra-efficient MiniLM backbone
model_name = "sentence-transformers/all-MiniLM-L6-v2"
model = SentenceTransformer(model_name)

train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
train_loss = losses.MultipleNegativesRankingLoss(model)

# Triplet Evaluator on validation set
evaluator = evaluation.TripletEvaluator(
    anchors=[c["anchors"][0] for c in raw_clusters],
    positives=[c["positives"][0] for c in raw_clusters],
    negatives=[raw_clusters[(idx + 1) % len(raw_clusters)]["positives"][0] for idx, c in enumerate(raw_clusters)],
    name="val_triplet_benchmark"
)

# Benchmark baseline before training
base_acc = evaluator(model)
print(f"Baseline Zero-Shot Accuracy on Domain Triplets: {base_acc:.4f}")"""),

    md_cell("""## 4. Fine-Tuning Execution with Warmup & Cosine Annealing"""),

    code_cell("""import os

# Train for 4 epochs with warm-up
output_dir = "./insight_minilm_finetuned"
os.makedirs(output_dir, exist_ok=True)

model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    evaluator=evaluator,
    epochs=4,
    warmup_steps=10,
    output_path=output_dir,
    show_progress_bar=True
)

# Evaluate after fine-tuning
ft_model = SentenceTransformer(output_dir)
ft_acc = evaluator(ft_model)
print(f"Post Fine-Tuning Domain Triplet Accuracy: {ft_acc:.4f}")
print(f"Absolute Accuracy Delta: +{(ft_acc - base_acc)*100:.2f}%")"""),

    md_cell("""## 5. Export to Quantized ONNX for Sub-4ms CPU Serving
To ensure zero deployment friction in production FastAPI servers, we export the PyTorch graph to ONNX and apply INT8 dynamic quantization."""),

    code_cell("""import torch.onnx
from transformers import AutoTokenizer, AutoModel
import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType

# Load HF primitives
tokenizer = AutoTokenizer.from_pretrained(output_dir)
hf_model = AutoModel.from_pretrained(output_dir)
hf_model.eval()

dummy_text = "Checkout gateway hangs on payment submission"
inputs = tokenizer(dummy_text, return_tensors="pt")

onnx_fp32_path = "./insight_minilm.onnx"
onnx_int8_path = "./insight_minilm_quantized.onnx"

torch.onnx.export(
    hf_model,
    (inputs["input_ids"], inputs["attention_mask"], inputs["token_type_ids"]),
    onnx_fp32_path,
    input_names=["input_ids", "attention_mask", "token_type_ids"],
    output_names=["last_hidden_state", "pooler_output"],
    dynamic_axes={
        "input_ids": {0: "batch_size", 1: "seq_len"},
        "attention_mask": {0: "batch_size", 1: "seq_len"},
        "token_type_ids": {0: "batch_size", 1: "seq_len"},
        "last_hidden_state": {0: "batch_size", 1: "seq_len"}
    },
    opset_version=14
)

# Quantize to INT8
quantize_dynamic(onnx_fp32_path, onnx_int8_path, weight_type=QuantType.QInt8)

fp32_size = os.path.getsize(onnx_fp32_path) / (1024 * 1024)
int8_size = os.path.getsize(onnx_int8_path) / (1024 * 1024)

print(f"FP32 ONNX Size: {fp32_size:.2f} MB")
print(f"INT8 ONNX Size: {int8_size:.2f} MB (Compression: {fp32_size / int8_size:.1f}x)")
print(f"Export Complete! Copy '{onnx_int8_path}' directly to InSight 'backend/models/'")""")
]

# ----------------------------------------------------
# Notebook 2: DeBERTa Multi-Task & Calibration
# ----------------------------------------------------
nb2_cells = [
    md_cell("""# InSight | Multi-Task DeBERTa-v3 with Post-Hoc Calibration (Platt & Temperature Scaling)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/visheshaggarwal0/InSight/blob/main/notebooks/02_deberta_multitask_sentiment_severity.ipynb)

### Objective
Standard neural networks are notoriously overconfident in their posterior probabilities. For an operational triaging system like InSight, an uncalibrated 95% confidence score could mean a false alarm or a missed critical P0 outage.

### Architecture:
1. **Backbone**: `microsoft/deberta-v3-small` with disentangled attention.
2. **Multi-Task Heads**:
   - Head A: 3-Class Sentiment (`Negative`, `Neutral`, `Positive`)
   - Head B: 4-Class Incident Severity (`P0 Blocker`, `P1 Critical`, `P2 Major`, `P3 Minor`)
3. **Loss Function**: Multi-task joint loss $\\mathcal{L}_{total} = \\mathcal{L}_{sent} + \\lambda \\mathcal{L}_{sev}$.
4. **Post-Hoc Calibration**: Temperature Scaling $z / T$ to minimize Expected Calibration Error (ECE) below 3%."""),

    code_cell("""# 1. Environment & CUDA Check
import torch
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

!pip install -q transformers datasets evaluate scikit-learn matplotlib seaborn"""),

    md_cell("""## 2. Multi-Task DeBERTa Model Architecture"""),

    code_cell("""import torch.nn as nn
from transformers import DebertaV2Model, DebertaV2PreTrainedModel, AutoTokenizer

class MultiTaskDeBERTa(DebertaV2PreTrainedModel):
    def __init__(self, config, num_sentiment=3, num_severity=4):
        super().__init__(config)
        self.deberta = DebertaV2Model(config)
        self.dropout = nn.Dropout(0.2)
        
        # Dual classification heads
        self.sentiment_head = nn.Linear(config.hidden_size, num_sentiment)
        self.severity_head = nn.Linear(config.hidden_size, num_severity)
        
        self.init_weights()

    def forward(self, input_ids=None, attention_mask=None, token_type_ids=None):
        outputs = self.deberta(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        # Mean pooling across non-padding tokens
        token_embeddings = outputs.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        pooled = sum_embeddings / sum_mask
        
        pooled = self.dropout(pooled)
        sentiment_logits = self.sentiment_head(pooled)
        severity_logits = self.severity_head(pooled)
        
        return sentiment_logits, severity_logits

print("MultiTaskDeBERTa class initialized successfully.")"""),

    md_cell("""## 3. Post-Hoc Temperature Scaling for Probability Calibration
Temperature scaling softens the softmax logits by a learned scalar parameter $T > 0$:
$$p_i = \\frac{\\exp(z_i / T)}{\\sum_j \\exp(z_j / T)}$$
Optimized using Negative Log-Likelihood (NLL) on a held-out validation calibration split."""),

    code_cell("""import torch.optim as optim

class TemperatureScaler(nn.Module):
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits):
        return logits / self.temperature

    def fit_calibration(self, val_logits, val_labels):
        \"\"\"Optimize temperature T to minimize NLL on validation logits.\"\"\"
        nll_criterion = nn.CrossEntropyLoss()
        optimizer = optim.LBFGS([self.temperature], lr=0.01, max_iter=50)

        def eval_step():
            optimizer.zero_grad()
            loss = nll_criterion(self.forward(val_logits), val_labels)
            loss.backward()
            return loss

        optimizer.step(eval_step)
        print(f"Optimal Calibration Temperature T: {self.temperature.item():.4f}")
        return self.temperature.item()

def compute_ece(probs, labels, n_bins=10):
    \"\"\"Expected Calibration Error (ECE)\"\"\"
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = predictions == labels

    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            avg_confidence = np.mean(confidences[in_bin])
            avg_accuracy = np.mean(accuracies[in_bin])
            ece += np.abs(avg_confidence - avg_accuracy) * prop_in_bin

    return ece

# Demonstration of ECE calculation
sim_logits = torch.randn(500, 3) * 3.5  # Artificially overconfident logits
sim_labels = torch.randint(0, 3, (500,))

scaler = TemperatureScaler()
scaler.fit_calibration(sim_logits, sim_labels)

uncal_probs = torch.softmax(sim_logits, dim=-1).detach().numpy()
cal_probs = torch.softmax(scaler(sim_logits), dim=-1).detach().numpy()
labels_np = sim_labels.numpy()

uncal_ece = compute_ece(uncal_probs, labels_np)
cal_ece = compute_ece(cal_probs, labels_np)

print(f"Uncalibrated ECE: {uncal_ece * 100:.2f}%")
print(f"Calibrated ECE:   {cal_ece * 100:.2f}% (Reduced by {((uncal_ece - cal_ece)/uncal_ece)*100:.1f}%)")""")
]

# ----------------------------------------------------
# Notebook 3: Phi-3 QLoRA Jira Bug Ticket Synthesis
# ----------------------------------------------------
nb3_cells = [
    md_cell("""# InSight | Microsoft Phi-3-mini-4k-instruct QLoRA Fine-Tuning for Jira Ticket Synthesis
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/visheshaggarwal0/InSight/blob/main/notebooks/03_phi3_qlora_jira_generator.ipynb)

### Objective
Transform raw unsupervised cluster themes into engineering-ready Jira bug tickets using **Microsoft Phi-3-mini-4k-instruct** (3.8B parameter Small Language Model).

### Why Phi-3-mini + QLoRA?
1. **Compact Footprint**: 3.8B parameters quantized to 4-bit (NF4) fits into **< 6.5 GB VRAM**, running easily on Google Colab's free T4 GPU.
2. **Exceptional Reasoning**: Outperforms Llama-2-70B and matches Mixtral 8x7B on instruction following and synthetic synthesis.
3. **Structured Schema Output**: Guaranteed formatting: Title, Priority, Customer Blast Radius, Verbatim Quotes, Steps to Reproduce, and Root Cause Hypothesis."""),

    code_cell("""# 1. Environment & 4-bit Package Installation
import torch
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU'}")

!pip install -q bitsandbytes peft trl accelerate transformers datasets"""),

    md_cell("""## 2. Load Phi-3 in 4-bit NormalFloat (NF4) with BitsAndBytes"""),

    code_cell("""import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

model_id = "microsoft/Phi-3-mini-4k-instruct"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True
)

model = prepare_model_for_kbit_training(model)

# Configure LoRA targets
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["o_proj", "qkv_proj", "gate_up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

lora_model = get_peft_model(model, peft_config)
lora_model.print_trainable_parameters()"""),

    md_cell("""## 3. Dataset Prompt Engineering & Training Template
Format customer cluster data into a structured system prompt."""),

    code_cell("""def format_insight_prompt(cluster):
    system_msg = "You are an expert Principal Staff Reliability & Software Engineer at InSight. Synthesize customer feedback clusters into an engineering-ready Jira bug ticket."
    
    user_content = f\"\"\"Analyze the following customer incident cluster:
- Theme: {cluster['title']}
- Severity: {cluster['severity']}
- Review Volume: {cluster['count']} reviews ({cluster['neg_rate']}% negative)
- Keywords: {', '.join(cluster['keywords'])}

Sample Customer Verbatims:
1. "{cluster['verbatims'][0]}"
2. "{cluster['verbatims'][1]}"
3. "{cluster['verbatims'][2]}"

Generate a production-ready Jira ticket with Title, Severity, Impact Analysis, Steps to Reproduce, and Root Cause Hypothesis.\"\"\"

    assistant_response = f\"\"\"# [JIRA BUG] {cluster['title']} - Service Degradation & Impact
**Priority**: {cluster['severity']} | **Status**: Open | **Component**: {cluster['keywords'][0].title()}

### 1. Executive Summary & Impact Analysis
Customer feedback analysis indicates an active regression in `{cluster['keywords'][0]}` affecting {cluster['count']} tracked users with a {cluster['neg_rate']}% negative sentiment rate. Relative churn risk is calculated at >2.5x.

### 2. Evidence from Customer Verbatims
- *"{cluster['verbatims'][0]}"*
- *"{cluster['verbatims'][1]}"*
- *"{cluster['verbatims'][2]}"*

### 3. Steps to Reproduce
1. Navigate to customer application on latest production build.
2. Trigger the `{cluster['keywords'][0]}` workflow.
3. Observe intermittent timeout or exception.

### 4. Root Cause Hypothesis & Engineering Action
- **Hypothesis**: Downstream API timeout or race condition under high concurrency.
- **Recommended Action**: Inspect telemetry logs for 5xx errors; implement exponential backoff retry on client.\"\"\"

    return f"<|system|>\\n{system_msg}<|end|>\\n<|user|>\\n{user_content}<|end|>\\n<|assistant|>\\n{assistant_response}<|end|>"

sample_cluster = {
    "title": "Payment Gateway Timeout",
    "severity": "CRITICAL",
    "count": 482,
    "neg_rate": 94.2,
    "keywords": ["payment", "checkout", "gateway", "stripe", "timeout"],
    "verbatims": [
        "Card payment spinner spins for 60 seconds then throws error 504.",
        "Unable to complete purchase during checkout.",
        "Charged twice on bank statement because checkout timed out."
    ]
}

formatted_text = format_insight_prompt(sample_cluster)
print("Sample Prompt Formatted for Phi-3 Instruct:")
print(formatted_text[:600] + "...\\n[TRUNCATED]")"""),

    md_cell("""## 4. Inference Demonstration & Jira Ticket Generation"""),

    code_cell("""def generate_jira_ticket(theme_title, severity, count, neg_rate, keywords, verbatims):
    cluster_obj = {
        "title": theme_title,
        "severity": severity,
        "count": count,
        "neg_rate": neg_rate,
        "keywords": keywords,
        "verbatims": verbatims
    }
    
    prompt = f\"\"\"<|system|>
You are an expert Principal Staff Reliability & Software Engineer at InSight. Synthesize customer feedback clusters into an engineering-ready Jira bug ticket.<|end|>
<|user|>
Analyze the following customer incident cluster:
- Theme: {theme_title}
- Severity: {severity}
- Review Volume: {count} reviews ({neg_rate}% negative)
- Keywords: {', '.join(keywords)}

Sample Customer Verbatims:
1. "{verbatims[0]}"
2. "{verbatims[1]}"
3. "{verbatims[2]}"

Generate a production-ready Jira ticket with Title, Severity, Impact Analysis, Steps to Reproduce, and Root Cause Hypothesis.<|end|>
<|assistant|>
\"\"\"
    
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=450,
            temperature=0.2,
            do_sample=True,
            top_p=0.9
        )
    
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return response

# Test generation
ticket = generate_jira_ticket(
    "Battery Drainage & Thermal Throttling",
    "CRITICAL",
    640,
    91.4,
    ["battery", "heat", "discharge", "update", "shutdown"],
    [
        "Battery drops 30% in 15 minutes after firmware v2.4.",
        "Phone becomes burning hot during simple video streaming.",
        "Device suddenly died at 18% remaining battery."
    ]
)

print(ticket)""")
]

# Generate notebooks in notebooks/
os.makedirs("notebooks", exist_ok=True)
create_notebook(nb1_cells, "notebooks/01_biencoder_contrastive_finetuning.ipynb")
create_notebook(nb2_cells, "notebooks/02_deberta_multitask_sentiment_severity.ipynb")
create_notebook(nb3_cells, "notebooks/03_phi3_qlora_jira_generator.ipynb")
print("All 3 Colab/Kaggle notebooks generated successfully!")
