"""scripts/download_models.py
Setup & verification script for InSight model artifacts and pretrained weights.

Usage:
    python scripts/download_models.py [--check-only] [--model-name NAME]

This script:
  1. Verifies that all required repository-tracked artifacts exist:
     - sentiment_pipeline.joblib
     - theme_centroids.npy
     - cluster_assignments.csv
     - cluster_representatives.csv
     - minilm_embeddings.npy
  2. Verifies the processed dataset:
     - cosmetics_10k.csv
  3. Pre-downloads and warms up the pinned sentence transformer model:
     - sentence-transformers/all-MiniLM-L6-v2
     into the local Hugging Face cache so future pipeline executions can run completely offline.
  4. Tests encoding a dummy sentence to confirm runtime readiness.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from InSight_ML.pipeline_config import (
    PROJECT_ROOT,
    ARTIFACTS,
    DATASETS,
    verify_artifacts,
)

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def check_artifacts() -> bool:
    """Check that all tracked offline ML artifacts and datasets exist."""
    print("=" * 70)
    print("InSight Artifact & Dataset Verification")
    print("=" * 70)
    print(f"Project root resolved to: {PROJECT_ROOT}\n")

    all_ok = True

    print("[1] Offline Model Artifacts:")
    for name, path in ARTIFACTS.items():
        exists = path.is_file()
        size_str = f"({path.stat().st_size / 1e3:.1f} KB)" if exists else "[MISSING]"
        status_tag = "  [PASS]" if exists else "  [FAIL]"
        print(f"{status_tag} {name:<26} -> {path.name:<32} {size_str}")
        if not exists:
            all_ok = False

    print("\n[2] Processed Datasets:")
    for name, path in DATASETS.items():
        exists = path.is_file()
        size_str = f"({path.stat().st_size / 1e6:.2f} MB)" if exists else "[MISSING]"
        status_tag = "  [PASS]" if exists else "  [FAIL]"
        print(f"{status_tag} {name:<26} -> {path.name:<32} {size_str}")
        if not exists:
            all_ok = False

    return all_ok


def warm_up_pretrained_model(model_name: str = DEFAULT_MODEL_NAME, check_only: bool = False) -> bool:
    """Download and test the sentence transformer embedding model."""
    print("\n[3] Pretrained Transformer Model:")
    print(f"  Model identifier: {model_name}")

    if check_only:
        print("  (--check-only mode active: skipping model download/warmup)")
        return True

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("  [FAIL] sentence-transformers package not installed. Run: pip install -r requirements.txt")
        return False

    print("  Connecting / verifying local cache for SentenceTransformer …")
    t0 = time.time()
    try:
        model = SentenceTransformer(model_name)
        elapsed = time.time() - t0
        print(f"  [PASS] Model loaded successfully in {elapsed:.2f}s")
    except Exception as exc:
        print(f"  [FAIL] Could not load or download model '{model_name}': {exc}")
        print("         Please check internet connection or pre-set HF_HOME cache.")
        return False

    # Test encoding
    print("  Testing test inference encoding …")
    test_vec = model.encode(["This is a test review text."], normalize_embeddings=True)
    if test_vec.shape == (1, 384):
        print(f"  [PASS] Output vector shape matches expected: {test_vec.shape}")
        return True
    else:
        print(f"  [FAIL] Unexpected vector shape: {test_vec.shape} (expected (1, 384))")
        return False


def main():
    parser = argparse.ArgumentParser(description="InSight Model & Artifact Setup")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check presence of artifacts without downloading pretrained models.",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=DEFAULT_MODEL_NAME,
        help=f"HuggingFace model identifier (default: {DEFAULT_MODEL_NAME})",
    )
    args = parser.parse_args()

    artifacts_ok = check_artifacts()
    model_ok = warm_up_pretrained_model(model_name=args.model_name, check_only=args.check_only)

    print("\n" + "=" * 70)
    if artifacts_ok and model_ok:
        print("RESULT: ALL IN-SIGHT PIPELINE DEPENDENCIES ARE VERIFIED & READY TO RUN.")
        print("=" * 70)
        sys.exit(0)
    else:
        print("RESULT: VERIFICATION FAILED. Please resolve missing dependencies above.")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
