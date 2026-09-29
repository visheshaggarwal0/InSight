"""InSight_ML/train_deberta.py
Fine-tunes microsoft/deberta-v3-small on the 2,000-sample balanced sentence dataset:
  - Classes: [COMPLAINT, RECOMMENDATION, PRAISE, NEUTRAL_NOISE]
  - Evaluation: Accuracy, Macro-F1, Per-class Precision/Recall on 400-sample test split
  - Optimization: Dynamic INT8 quantization on nn.Linear layers for CPU acceleration
  - Export: Saves both FP32 and INT8 weights to InSight_ML/outputs/deberta_extractor/

Can be run locally or uploaded directly into a Kaggle T4 notebook.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_deberta")

# Target labels
LABEL_MAP = {
    "COMPLAINT": 0,
    "RECOMMENDATION": 1,
    "PRAISE": 2,
    "NEUTRAL_NOISE": 3
}
INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ds_candidate = PROJECT_ROOT / "data" / "processed" / "complaint_sentences_2k.json"
DATASET_PATH = _ds_candidate if _ds_candidate.exists() else PROJECT_ROOT / "InSight_ML" / "data" / "processed" / "complaint_sentences_2k.json"
_out_candidate = PROJECT_ROOT / "outputs" / "deberta_extractor"
OUTPUT_DIR = _out_candidate if (PROJECT_ROOT / "outputs").exists() else PROJECT_ROOT / "InSight_ML" / "outputs" / "deberta_extractor"


class SentenceDataset(Dataset):
    def __init__(self, samples: List[Dict[str, Any]], tokenizer, max_len: int = 128):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        item = self.samples[idx]
        text = str(item["text"])
        label_id = LABEL_MAP[item["label"]]

        encoding = self.tokenizer(
            text,
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(label_id, dtype=torch.long)
        }


def evaluate(model, dataloader, device) -> Tuple[Dict[str, Any], np.ndarray, np.ndarray]:
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            preds = torch.argmax(logits, dim=-1).cpu().numpy()

            all_preds.extend(preds)
            all_labels.extend(labels.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    acc = accuracy_score(all_labels, all_preds)
    macro_f1 = f1_score(all_labels, all_preds, average="macro")
    weighted_f1 = f1_score(all_labels, all_preds, average="weighted")
    report = classification_report(
        all_labels,
        all_preds,
        target_names=[INV_LABEL_MAP[i] for i in range(4)],
        output_dict=True
    )
    cm = confusion_matrix(all_labels, all_preds).tolist()

    metrics = {
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "classification_report": report,
        "confusion_matrix": cm
    }
    return metrics, all_labels, all_preds


def train(
    dataset_path: Path = DATASET_PATH,
    output_dir: Path = OUTPUT_DIR,
    model_name: str = "microsoft/deberta-v3-small",
    batch_size: int = 32,
    epochs: int = 4,
    learning_rate: float = 3e-5,
    max_len: int = 128
):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training Device: %s", device)

    # 1. Load dataset (supports both CSV and JSON)
    if not dataset_path.exists():
        csv_fallback = dataset_path.with_suffix(".csv")
        if csv_fallback.exists():
            dataset_path = csv_fallback
        else:
            raise FileNotFoundError(f"Dataset not found at {dataset_path} or {csv_fallback}. Run generate_complaint_dataset.py first.")

    if str(dataset_path).endswith(".csv"):
        import pandas as pd
        df = pd.read_csv(dataset_path)
        train_samples = df[df["split"] == "train"].to_dict(orient="records")
        val_samples = df[df["split"] == "val"].to_dict(orient="records")
        total_count = len(df)
    else:
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        train_samples = [s for s in data["samples"] if s["split"] == "train"]
        val_samples = [s for s in data["samples"] if s["split"] == "val"]
        total_count = len(data["samples"])

    logger.info("Loaded %d train samples and %d validation samples from %s.", len(train_samples), len(val_samples), dataset_path.name)

    # 2. Tokenizer & Datasets
    logger.info("Initializing tokenizer '%s'...", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    train_dataset = SentenceDataset(train_samples, tokenizer, max_len=max_len)
    val_dataset = SentenceDataset(val_samples, tokenizer, max_len=max_len)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # 3. Model setup
    logger.info("Loading model '%s' with 4 classes...", model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=4,
        id2label=INV_LABEL_MAP,
        label2id=LABEL_MAP
    )
    model.to(device)

    # Cost-sensitive weighting (slight up-weight on COMPLAINT for higher recall)
    class_weights = torch.tensor([1.2, 1.0, 1.0, 1.0], dtype=torch.float).to(device)
    loss_fn = nn.CrossEntropyLoss(weight=class_weights)

    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    lr_scheduler = torch.optim.lr_scheduler.LinearLR(optimizer, start_factor=0.1, total_iters=max(1, int(total_steps * 0.1)))

    # 4. Training loop
    logger.info("Starting training (%d epochs, %d batches per epoch)...", epochs, len(train_loader))
    t0 = time.time()
    best_f1 = 0.0

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            loss = loss_fn(outputs.logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

            optimizer.step()
            lr_scheduler.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)
        val_metrics, _, _ = evaluate(model, val_loader, device)

        logger.info(
            "Epoch %d/%d | Train Loss: %.4f | Val Acc: %.4f | Val Macro-F1: %.4f | Complaint F1: %.4f",
            epoch, epochs, avg_loss, val_metrics["accuracy"], val_metrics["macro_f1"],
            val_metrics["classification_report"]["COMPLAINT"]["f1-score"]
        )

        if val_metrics["macro_f1"] > best_f1:
            best_f1 = val_metrics["macro_f1"]

    training_time = time.time() - t0
    logger.info("Training completed in %.2f seconds. Best Val F1: %.4f", training_time, best_f1)

    # 5. Final Evaluation on Validation Split
    final_metrics, _, _ = evaluate(model, val_loader, device)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Save FP32 Model & Tokenizer
    fp32_dir = output_dir / "deberta_fp32"
    fp32_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(fp32_dir)
    tokenizer.save_pretrained(fp32_dir)
    logger.info("Saved FP32 model to %s", fp32_dir)

    # 6. Apply Dynamic INT8 Quantization (CPU)
    logger.info("Quantizing model to INT8 (targeting nn.Linear layers)...")
    cpu_model = model.cpu()
    cpu_model.eval()

    quantized_model = torch.ao.quantization.quantize_dynamic(
        cpu_model,
        {nn.Linear},
        dtype=torch.qint8
    )

    int8_dir = output_dir / "deberta_int8"
    int8_dir.mkdir(parents=True, exist_ok=True)
    torch.save(quantized_model.state_dict(), int8_dir / "pytorch_model_int8.bin")
    tokenizer.save_pretrained(int8_dir)
    cpu_model.config.save_pretrained(int8_dir)
    logger.info("Saved INT8 quantized weights to %s", int8_dir)

    # Latency Benchmark: FP32 vs INT8 on CPU
    test_texts = [s["text"] for s in val_samples[:50]]
    enc = tokenizer(test_texts, padding=True, truncation=True, max_length=max_len, return_tensors="pt")

    # Benchmark FP32
    t_start = time.time()
    with torch.no_grad():
        for _ in range(5):
            _ = cpu_model(**enc)
    fp32_latency_ms = ((time.time() - t_start) / (5 * len(test_texts))) * 1000

    # Benchmark INT8
    t_start = time.time()
    with torch.no_grad():
        for _ in range(5):
            _ = quantized_model(**enc)
    int8_latency_ms = ((time.time() - t_start) / (5 * len(test_texts))) * 1000

    logger.info("Latency Benchmark (CPU): FP32 = %.2f ms/sent | INT8 = %.2f ms/sent (%.1fx speedup)",
                fp32_latency_ms, int8_latency_ms, fp32_latency_ms / max(1e-6, int8_latency_ms))

    # Save benchmark & validation report
    benchmark_payload = {
        "model_name": model_name,
        "training_time_sec": round(training_time, 2),
        "dataset": {
            "total_samples": len(data["samples"]),
            "train_samples": len(train_samples),
            "val_samples": len(val_samples)
        },
        "validation_metrics": final_metrics,
        "latency_benchmark_cpu": {
            "fp32_ms_per_sentence": round(fp32_latency_ms, 2),
            "int8_ms_per_sentence": round(int8_latency_ms, 2),
            "speedup_factor": round(fp32_latency_ms / max(1e-6, int8_latency_ms), 2)
        }
    }

    with open(output_dir / "training_metrics.json", "w", encoding="utf-8") as f:
        json.dump(benchmark_payload, f, indent=2)

    print("\n" + "=" * 70)
    print("TRAINING & QUANTIZATION COMPLETED")
    print(f"  Accuracy: {final_metrics['accuracy'] * 100:.1f}%")
    print(f"  Macro-F1: {final_metrics['macro_f1'] * 100:.1f}%")
    print(f"  Complaint F1: {final_metrics['classification_report']['COMPLAINT']['f1-score'] * 100:.1f}%")
    print(f"  Recommendation F1: {final_metrics['classification_report']['RECOMMENDATION']['f1-score'] * 100:.1f}%")
    print(f"  CPU INT8 Latency: {int8_latency_ms:.2f} ms/sentence ({fp32_latency_ms / max(1e-6, int8_latency_ms):.1f}x speedup)")
    print(f"  Model saved to: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DeBERTa-v3 Complaint Extractor")
    parser.add_argument("--epochs", type=int, default=4, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for training")
    parser.add_argument("--lr", type=float, default=3e-5, help="Learning rate")
    args = parser.parse_args()

    train(epochs=args.epochs, batch_size=args.batch_size, learning_rate=args.lr)
