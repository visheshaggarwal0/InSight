import numpy as np
from typing import Dict, Any, List
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    brier_score_loss,
    log_loss,
)
from sklearn.calibration import calibration_curve


class ModelEvaluationHarness:
    """
    Rigorously validates model accuracy, calibration, and confusion matrix
    against held-out ground truth labeled test samples.

    Every metric is computed on the supplied arrays only; nothing is fitted
    here, so this harness cannot leak the evaluation set into a model.
    """

    @staticmethod
    def evaluate(
        y_true: List[str],
        y_pred: List[str],
        y_probs: np.ndarray,
        classes: List[str]
    ) -> Dict[str, Any]:
        """
        Generates enterprise governance metrics.

        ``y_probs`` must be an (n_samples, n_classes) array whose column order
        matches ``classes``.
        """
        y_true = list(y_true)
        y_pred = list(y_pred)

        if not y_true:
            raise ValueError("Cannot evaluate on an empty ground-truth sample.")
        if len(y_true) != len(y_pred):
            raise ValueError("y_true and y_pred must be the same length.")

        y_probs = np.asarray(y_probs, dtype=float)
        if y_probs.ndim != 2 or y_probs.shape[1] != len(classes):
            raise ValueError(
                f"y_probs must have shape (n_samples, {len(classes)}), got {y_probs.shape}."
            )
        if y_probs.shape[0] != len(y_true):
            raise ValueError("y_probs row count does not match the number of labelled samples.")

        acc = accuracy_score(y_true, y_pred)
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, labels=classes, zero_division=0
        )
        macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
            y_true, y_pred, labels=classes, average='macro', zero_division=0
        )

        cm = confusion_matrix(y_true, y_pred, labels=classes)

        per_class_metrics = {}
        for idx, cls in enumerate(classes):
            per_class_metrics[cls] = {
                "precision": round(float(precision[idx]), 4),
                "recall": round(float(recall[idx]), 4),
                "f1_score": round(float(f1[idx]), 4),
                "support": int(support[idx])
            }

        # Multi-class Brier score: mean squared error of the full probability
        # vector against the one-hot target (per ARCHITECTURE.md section 6.2).
        class_index = {cls: i for i, cls in enumerate(classes)}
        one_hot = np.zeros_like(y_probs)
        for row, label in enumerate(y_true):
            idx = class_index.get(label)
            if idx is not None:
                one_hot[row, idx] = 1.0
        brier = float(np.mean(np.sum((y_probs - one_hot) ** 2, axis=1)))

        # Reliability diagram data so calibration is auditable, not just asserted.
        reliability = []
        for idx, cls in enumerate(classes):
            try:
                frac_pos, mean_pred = calibration_curve(
                    (np.array(y_true) == cls).astype(int), y_probs[:, idx], n_bins=10, strategy="uniform"
                )
                reliability.append({
                    "class": cls,
                    "bins": [
                        {"mean_predicted": round(float(m), 4), "fraction_positive": round(float(f), 4)}
                        for m, f in zip(mean_pred, frac_pos)
                    ],
                })
            except ValueError:
                # A class with a single unique probability value has no
                # meaningful reliability curve; record it as unavailable
                # rather than silently dropping the class.
                reliability.append({"class": cls, "bins": [], "note": "insufficient variation"})

        # Present-class coverage: fraction of the gold sample whose label is
        # one of the classes the model can actually emit. Exposes a gold set
        # that drifted out of the model's label space instead of hiding it.
        coverage = float(np.mean([label in class_index for label in y_true]))

        return {
            "sample_size": len(y_true),
            "accuracy": round(float(acc), 4),
            "macro_precision": round(float(macro_p), 4),
            "macro_recall": round(float(macro_r), 4),
            "macro_f1": round(float(macro_f1), 4),
            "brier_score": round(brier, 4),
            "label_coverage": round(coverage, 4),
            "classes": classes,
            "confusion_matrix": cm.tolist(),
            "per_class": per_class_metrics,
            "reliability": reliability,
        }

    @staticmethod
    def safe_log_loss(y_true: List[str], y_probs: np.ndarray, classes: List[str]) -> float | None:
        """Multiclass log loss, or ``None`` when the gold sample covers a single class."""
        unique = set(y_true)
        if len(unique) < 2:
            return None
        return round(float(log_loss(y_true, np.asarray(y_probs, dtype=float), labels=classes)), 4)


evaluation_harness = ModelEvaluationHarness()
