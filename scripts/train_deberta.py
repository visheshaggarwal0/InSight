"""scripts/train_deberta.py
Fine-tunes microsoft/deberta-v3-small on the ~2,000-sample sentence intent dataset.

Classes: [COMPLAINT, RECOMMENDATION, PRAISE, NEUTRAL_NOISE]

IMPORTANT HONESTY NOTES — read before quoting any number from
`training_metrics.json`:
  - The dataset is SYNTHETIC for the `tech_saas` half and sampled from real
    (unlabelled) Sephora reviews for the `d2c_cosmetics` half. Its labels come
    from KEYWORD HEURISTICS, not from human annotation. Metrics below measure
    agreement with those heuristics, NOT real-world accuracy.
  - There is NO independent test split. The only held-out data is the same
    `val` split used to select the best epoch, so the reported validation
    metrics are selection-biased / optimistic. See `has_independent_test_split`.
  - Class distribution is NOT balanced (COMPLAINT is the largest class).

Runtime features:
  - Mixed precision (bf16 autocast on CUDA, fp32 on CPU)
  - Dynamic padding (no fixed 128-token pad on every sentence)
  - Gradient accumulation + linear warmup/decay schedule
  - Deterministic seeding (`--seed`) so metrics are reproducible
  - Per-epoch checkpointing + resume (survives Kaggle session death)
  - Dynamic INT8 quantization for CPU serving, with INT8 accuracy measured

Optimization: Dynamic INT8 quantization on nn.Linear layers for CPU acceleration
Export: Saves both FP32 and INT8 weights to outputs/deberta_extractor/

Can be run locally or uploaded directly into a Kaggle T4 notebook.
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
N_LABELS = len(LABEL_MAP)
# Always score all 4 labels explicitly so "Macro-F1" and the confusion matrix
# keep the same meaning across runs even when a class is absent from a split.
ALL_LABEL_IDS = list(range(N_LABELS))
ALL_LABEL_NAMES = [INV_LABEL_MAP[i] for i in range(N_LABELS)]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ds_candidate = PROJECT_ROOT / "data" / "processed" / "complaint_sentences_2k.json"
DATASET_PATH = _ds_candidate if _ds_candidate.exists() else PROJECT_ROOT / "data" / "processed" / "complaint_sentences_2k.json"
_out_candidate = PROJECT_ROOT / "outputs" / "deberta_extractor"
OUTPUT_DIR = _out_candidate if (PROJECT_ROOT / "outputs").exists() else PROJECT_ROOT / "outputs" / "deberta_extractor"

# NOTE: max_len is also hard-coded in backend/app/ml/sentence_pipeline.py
# (owned elsewhere). Both are 128, which is comfortably above the ~20-token mean
# sentence length in this corpus. Keep the two in sync if either changes.
DEFAULT_MAX_LEN = 128


def set_seed(seed: int) -> None:
    """Seed every RNG that can influence training."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


class SentenceDataset(Dataset):
    """Raw-text dataset; tokenisation happens in the collate_fn.

    Tokenising per-item and then padding every tensor to `max_len` wastes ~84%
    of each batch on <pad> tokens. Instead the collator tokenises the whole
    batch and pads dynamically to the longest member.
    """

    def __init__(self, samples: List[Dict[str, Any]], tokenizer, max_len: int = DEFAULT_MAX_LEN):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        item = self.samples[idx]
        return {
            "text": str(item["text"]),
            "label": LABEL_MAP[item["label"]],
        }


def make_collate_fn(tokenizer, max_len: int):
    def collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        encodings = tokenizer(
            [b["text"] for b in batch],
            max_length=max_len,
            padding=True,           # dynamic: pad to longest in batch, not to max_len
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encodings["input_ids"],
            "attention_mask": encodings["attention_mask"],
            "labels": torch.tensor([b["label"] for b in batch], dtype=torch.long),
        }

    return collate_fn


def evaluate(model, dataloader, device, use_amp: bool = False) -> Dict[str, Any]:
    """Evaluate and return metrics. `labels=ALL_LABEL_IDS` pins the definition."""
    model.eval()
    all_preds: List[int] = []
    all_labels: List[int] = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            attention_mask = batch["attention_mask"].to(device, non_blocking=True)
            labels = batch["labels"].to(device, non_blocking=True)

            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_amp):
                logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
            preds = torch.argmax(logits, dim=-1).cpu().numpy()

            all_preds.extend(int(p) for p in preds)
            all_labels.extend(int(l) for l in labels.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    acc = accuracy_score(all_labels, all_preds)
    macro_f1 = f1_score(all_labels, all_preds, labels=ALL_LABEL_IDS, average="macro", zero_division=0)
    weighted_f1 = f1_score(all_labels, all_preds, labels=ALL_LABEL_IDS, average="weighted", zero_division=0)
    report = classification_report(
        all_labels,
        all_preds,
        labels=ALL_LABEL_IDS,
        target_names=ALL_LABEL_NAMES,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(all_labels, all_preds, labels=ALL_LABEL_IDS).tolist()

    return {
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "classification_report": report,
        "confusion_matrix": cm,
    }


def compute_class_weights(train_samples: List[Dict[str, Any]], device) -> Tuple[Optional[torch.Tensor], Dict[str, Any]]:
    """Inverse-frequency class weights derived from the ACTUAL train distribution.

    Previously this hard-coded [1.2, 1.0, 1.0, 1.0] to "up-weight COMPLAINT for
    recall", which is backwards: COMPLAINT is class 0 AND the LARGEST class, so
    that up-weighted the majority class. Returns (weights_or_None, distribution).
    """
    counts = {INV_LABEL_MAP[i]: 0 for i in range(N_LABELS)}
    for s in train_samples:
        counts[s["label"]] = counts.get(s["label"], 0) + 1
    total = max(sum(counts.values()), 1)
    present = [c for c in counts.values() if c > 0]

    weights = []
    for i in range(N_LABELS):
        c = counts[INV_LABEL_MAP[i]]
        if c == 0:
            weights.append(0.0)  # class absent from train: never appears as a target
        else:
            weights.append(len(present) / (N_LABELS * c))
    dist = {k: {"n": v, "pct": round(100.0 * v / total, 2)} for k, v in counts.items()}
    logger.info("Train class distribution: %s", dist)

    if sum(weights) == 0:
        return None, dist
    return torch.tensor(weights, dtype=torch.float, device=device), dist


def _save_checkpoint(path: Path, model, optimizer, scheduler, epoch: int, best_f1: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "best_macro_f1": best_f1,
        },
        path,
    )


def _load_checkpoint(path: Path, model, optimizer, scheduler) -> Tuple[int, float]:
    if not path.exists():
        return 0, 0.0
    # weights_only=True: our checkpoint is a plain dict of tensors/scalars, so
    # there is no reason to allow arbitrary pickle deserialization here.
    ckpt = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"])
    optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    scheduler.load_state_dict(ckpt["scheduler_state_dict"])
    logger.info("Resumed from checkpoint %s (epoch %d)", path.name, ckpt.get("epoch", 0))
    return int(ckpt.get("epoch", 0)), float(ckpt.get("best_macro_f1", 0.0))


def _pin_threads(n: Optional[int] = None) -> None:
    """Pin thread count so CPU latency numbers are reproducible."""
    if n is None:
        n = max(1, (os.cpu_count() or 2))
    torch.set_num_threads(n)
    logger.info("torch threads pinned to %d", torch.get_num_threads())


def benchmark_latency(model, tokenizer, texts: List[str], max_len: int, reps: int = 3) -> Dict[str, float]:
    """Report BOTH single-item latency and batched throughput, with warmup.

    Amortising a 50-sequence forward pass to a per-sentence figure understates
    true single-request latency (thread parallelism + cache locality), so the
    two are measured and reported separately.
    """
    model.eval()
    out: Dict[str, float] = {}

    # --- Single-item latency (batch_size=1) ---
    single = tokenizer(texts, padding=True, truncation=True, max_length=max_len, return_tensors="pt")
    # Warmup: first call pays lazy init / memory-arena costs and must not be timed.
    with torch.no_grad():
        for _ in range(3):
            model(**single)
    t0 = time.time()
    with torch.no_grad():
        for _ in range(reps):
            model(**single)
    elapsed = time.time() - t0
    out["batch1_ms_per_sequence"] = round(elapsed / reps * 1000, 2)

    # --- Batched throughput ---
    batch = tokenizer(
        texts, padding="max_length", truncation=True, max_length=max_len, return_tensors="pt"
    )
    with torch.no_grad():
        for _ in range(2):
            model(**batch)
    t0 = time.time()
    with torch.no_grad():
        for _ in range(reps):
            model(**batch)
    elapsed = time.time() - t0
    out["batched_ms_per_sequence"] = round(elapsed / reps / max(len(texts), 1) * 1000, 3)
    out["batched_sequences_per_sec"] = round(len(texts) * reps / max(elapsed, 1e-9), 1)
    return out


def train(
    dataset_path: Path = DATASET_PATH,
    output_dir: Path = OUTPUT_DIR,
    model_name: str = "microsoft/deberta-v3-small",
    batch_size: int = 32,
    epochs: int = 4,
    learning_rate: float = 3e-5,
    max_len: int = DEFAULT_MAX_LEN,
    seed: int = 42,
    grad_accum_steps: int = 1,
    num_workers: int = 2,
    resume: bool = True,
):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup

    set_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = device.type == "cuda"
    logger.info("Training Device: %s (amp=%s) seed=%d", device, use_amp, seed)

    # 1. Load dataset (supports both CSV and JSON)
    dataset_path = Path(dataset_path)
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
        # `data` is only bound in the JSON branch below; using it here was a
        # NameError on the CSV path.
        total_count = len(df)
    else:
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        train_samples = [s for s in data["samples"] if s["split"] == "train"]
        val_samples = [s for s in data["samples"] if s["split"] == "val"]
        total_count = len(data["samples"])

    if not train_samples:
        raise ValueError(
            f"No training rows in {dataset_path.name} "
            f"(total={total_count}). Refusing to divide by zero."
        )
    if not val_samples:
        raise ValueError(
            f"No validation rows in {dataset_path.name} "
            f"(total={total_count}). Refusing to evaluate on an empty set."
        )

    logger.info("Loaded %d train samples and %d validation samples from %s.", len(train_samples), len(val_samples), dataset_path.name)

    # 2. Tokenizer & Datasets
    logger.info("Initializing tokenizer '%s'...", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    collate_fn = make_collate_fn(tokenizer, max_len)

    generator = torch.Generator()
    generator.manual_seed(seed)

    def build_loader(samples, bs, shuffle):
        return DataLoader(
            SentenceDataset(samples, tokenizer, max_len=max_len),
            batch_size=bs,
            shuffle=shuffle,
            num_workers=num_workers,                 # tokenisation in collate_fn
            pin_memory=(device.type == "cuda"),
            collate_fn=collate_fn,
            generator=generator if shuffle else None,
            persistent_workers=(num_workers > 0),
        )

    train_loader = build_loader(train_samples, batch_size, shuffle=True)
    val_loader = build_loader(val_samples, batch_size, shuffle=False)

    # 3. Model setup
    logger.info("Loading model '%s' with %d classes...", model_name, N_LABELS)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=N_LABELS,
        id2label=INV_LABEL_MAP,
        label2id=LABEL_MAP
    )
    model.to(device)

    # Cost-sensitive weighting: inverse frequency from the REAL train split.
    class_weights, class_distribution = compute_class_weights(train_samples, device)
    loss_fn = nn.CrossEntropyLoss(weight=class_weights)
    logger.info("Class weights: %s", None if class_weights is None else class_weights.tolist())

    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    steps_per_epoch = max(1, len(train_loader) // max(1, grad_accum_steps))
    total_steps = steps_per_epoch * epochs
    num_warmup_steps = max(1, int(total_steps * 0.1))
    # Linear warmup 0 -> 1 then LINEAR DECAY TO ZERO over the remaining steps.
    # LinearLR held flat at 1.0x for 90% of training, which is not a schedule.
    lr_scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=num_warmup_steps, num_training_steps=total_steps
    )
    logger.info(
        "Schedule: %d total optimizer steps, %d warmup, grad_accum=%d",
        total_steps, num_warmup_steps, grad_accum_steps,
    )

    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    # 4. Training loop
    output_dir = Path(output_dir)
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    last_ckpt = checkpoint_dir / "last.pt"

    start_epoch = 1
    best_f1 = 0.0
    if resume:
        start_epoch, best_f1 = _load_checkpoint(last_ckpt, model, optimizer, lr_scheduler)
        start_epoch += 1

    best_state: Optional[Dict[str, torch.Tensor]] = None
    current_batch = batch_size
    logger.info("Starting training (%d epochs, %d batches per epoch)...", epochs, len(train_loader))
    t0 = time.time()

    for epoch in range(start_epoch, epochs + 1):
        model.train()
        total_loss = 0.0
        n_steps = 0
        optimizer.zero_grad(set_to_none=True)

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            attention_mask = batch["attention_mask"].to(device, non_blocking=True)
            labels = batch["labels"].to(device, non_blocking=True)

            try:
                with torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_amp):
                    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                    loss = loss_fn(outputs.logits, labels)
            except torch.cuda.OutOfMemoryError:
                if current_batch <= 1:
                    raise
                # Halve the batch size once and retry this same step.
                current_batch = max(1, current_batch // 2)
                logger.warning(
                    "CUDA OOM at batch_size=%d. Halving to %d and retrying.",
                    current_batch * 2, current_batch,
                )
                optimizer.zero_grad(set_to_none=True)
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                train_loader = build_loader(train_samples, current_batch, shuffle=True)
                continue

            loss = loss / max(1, grad_accum_steps)
            scaler.scale(loss).backward()

            if (step + 1) % max(1, grad_accum_steps) == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                lr_scheduler.step()
                optimizer.zero_grad(set_to_none=True)

            total_loss += loss.item()
            n_steps += 1

        avg_loss = total_loss / max(n_steps, 1)
        val_metrics = evaluate(model, val_loader, device, use_amp=use_amp)

        logger.info(
            "Epoch %d/%d | Train Loss: %.4f | Val Acc: %.4f | Val Macro-F1: %.4f | Complaint F1: %.4f",
            epoch, epochs, avg_loss, val_metrics["accuracy"], val_metrics["macro_f1"],
            val_metrics["classification_report"]["COMPLAINT"]["f1-score"]
        )

        if val_metrics["macro_f1"] > best_f1:
            best_f1 = val_metrics["macro_f1"]
            # Keep the BEST epoch's weights, not the last epoch's.
            best_state = copy.deepcopy(
                {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            )
            logger.info("  New best Val Macro-F1: %.4f (snapshot kept)", best_f1)

        _save_checkpoint(checkpoint_dir / f"epoch{epoch}.pt", model, optimizer, lr_scheduler, epoch, best_f1)
        _save_checkpoint(last_ckpt, model, optimizer, lr_scheduler, epoch, best_f1)

    training_time = time.time() - t0
    logger.info("Training completed in %.2f seconds. Best Val F1: %.4f", training_time, best_f1)

    if best_state is not None:
        logger.info("Restoring best-epoch weights (epoch-selection macro-F1=%.4f)", best_f1)
        model.load_state_dict(best_state)
    else:
        logger.warning("No epoch improved on the initial macro-F1; using final-epoch weights.")

    # 5. Final evaluation. NOTE: this is the SAME split used for epoch
    # selection, so these numbers are optimistic and are labelled as such.
    final_metrics = evaluate(model, val_loader, device, use_amp=use_amp)

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

    # 7. Measure INT8 accuracy. int8_dir is the ONLY artifact written for CPU
    # serving, so an unmeasured FP32-only report would ship an unverified model.
    int8_loader = DataLoader(
        SentenceDataset(val_samples, tokenizer, max_len=max_len),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        collate_fn=collate_fn,
    )
    int8_metrics = evaluate(quantized_model, int8_loader, torch.device("cpu"), use_amp=False)
    f1_drop = round(final_metrics["macro_f1"] - int8_metrics["macro_f1"], 4)
    if f1_drop > 0.01:
        logger.warning(
            "INT8 macro-F1 dropped %.4f (%.4f -> %.4f) versus FP32. Re-check serving config.",
            f1_drop, final_metrics["macro_f1"], int8_metrics["macro_f1"],
        )

    # 8. Latency benchmark (CPU): FP32 vs INT8, latency AND throughput separately
    _pin_threads()
    test_texts = [str(s["text"]) for s in val_samples[:50]]
    fp32_bench = benchmark_latency(cpu_model, tokenizer, test_texts, max_len)
    int8_bench = benchmark_latency(quantized_model, tokenizer, test_texts, max_len)
    latency_speedup = round(
        fp32_bench["batch1_ms_per_sequence"] / max(1e-6, int8_bench["batch1_ms_per_sequence"]), 2
    )
    logger.info(
        "CPU latency (batch=1, warmed up): FP32 = %.2f ms | INT8 = %.2f ms (%.2fx)",
        fp32_bench["batch1_ms_per_sequence"], int8_bench["batch1_ms_per_sequence"], latency_speedup,
    )

    # 9. Save benchmark & metrics report
    benchmark_payload = {
        "model_name": model_name,
        "seed": seed,
        "training_time_sec": round(training_time, 2),
        "dataset": {
            "total_samples": total_count,
            "train_samples": len(train_samples),
            "val_samples": len(val_samples),
            "class_distribution": class_distribution,
            "is_synthetic": True,
        },
        "has_independent_test_split": False,
        "best_epoch_val_macro_f1": round(best_f1, 4),
        "validation_metrics": {
            **final_metrics,
            "note": (
                "SAME split used for epoch selection. Optimistic: no independent "
                "test split exists. Not a real-world accuracy claim (labels are "
                "keyword-heuristic, dataset is partly synthetic)."
            ),
        },
        "int8_metrics": {
            **int8_metrics,
            "macro_f1_drop_vs_fp32": f1_drop,
            "note": "Dynamic INT8 on the CPU-serving artifact that is actually shipped.",
        },
        "latency_benchmark_cpu": {
            "note": "batch=1 figure is single-request latency; batched figure is throughput.",
            "fp32": fp32_bench,
            "int8": int8_bench,
            "speedup_factor_batch1": latency_speedup,
        },
    }

    with open(output_dir / "training_metrics.json", "w", encoding="utf-8") as f:
        json.dump(benchmark_payload, f, indent=2, allow_nan=False)

    print("\n" + "=" * 70)
    print("TRAINING & QUANTIZATION COMPLETED")
    print("  NOTE: synthetic/heuristic labels; no independent test split. Not a real-world accuracy claim.")
    print(f"  Val Accuracy (epoch-selection split): {final_metrics['accuracy'] * 100:.1f}%")
    print(f"  Val Macro-F1   (epoch-selection split): {final_metrics['macro_f1'] * 100:.1f}%")
    print(f"  INT8 Macro-F1  (epoch-selection split): {int8_metrics['macro_f1'] * 100:.1f}% (drop {f1_drop:.4f})")
    print(f"  Complaint F1: {final_metrics['classification_report']['COMPLAINT']['f1-score'] * 100:.1f}%")
    print(f"  Recommendation F1: {final_metrics['classification_report']['RECOMMENDATION']['f1-score'] * 100:.1f}%")
    print(f"  CPU INT8 latency (batch=1): {int8_bench['batch1_ms_per_sequence']:.2f} ms/sequence ({latency_speedup:.2f}x)")
    print(f"  CPU INT8 throughput (batched): {int8_bench['batched_sequences_per_sec']:.0f} seq/sec")
    print(f"  Model saved to: {output_dir}")
    print("=" * 70)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Train DeBERTa-v3 Sentence Intent Classifier")
    parser.add_argument("--epochs", type=int, default=4, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for training")
    parser.add_argument("--lr", type=float, default=3e-5, help="Learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Seed for full determinism")
    parser.add_argument("--max-len", type=int, default=DEFAULT_MAX_LEN, help="Max sequence length")
    parser.add_argument("--grad-accum-steps", type=int, default=1, help="Gradient accumulation steps")
    parser.add_argument("--num-workers", type=int, default=2, help="DataLoader workers (tokenisation)")
    parser.add_argument("--no-resume", action="store_true", help="Ignore any existing checkpoint")
    args = parser.parse_args(argv)

    train(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        seed=args.seed,
        max_len=args.max_len,
        grad_accum_steps=args.grad_accum_steps,
        num_workers=args.num_workers,
        resume=not args.no_resume,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
