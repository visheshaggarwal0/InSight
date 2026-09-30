import numpy as np
from typing import Dict, Any, List
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    brier_score_loss
)
from sklearn.calibration import calibration_curve

class ModelEvaluationHarness:
    """
    Rigorously validates model accuracy, calibration, and confusion matrix
    against held-out ground truth labeled test samples.
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
        """
        acc = accuracy_score(y_true, y_pred)
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, labels=classes, zero_division=0
        )
        macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='macro', zero_division=0
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

        # Multi-class Brier score proxy
        brier_scores = []
        for idx, cls in enumerate(classes):
            binary_true = [1 if y == cls else 0 for y in y_true]
            if idx < y_probs.shape[1]:
                brier_scores.append(brier_score_loss(binary_true, y_probs[:, idx]))
            else:
                brier_scores.append(brier_score_loss(binary_true, np.zeros(len(binary_true))))
        avg_brier = float(np.mean(brier_scores)) if brier_scores else 0.0

        return {
            "sample_size": len(y_true),
            "accuracy": round(float(acc), 4),
            "macro_precision": round(float(macro_p), 4),
            "macro_recall": round(float(macro_r), 4),
            "macro_f1": round(float(macro_f1), 4),
            "brier_score": round(avg_brier, 4),
            "classes": classes,
            "confusion_matrix": cm.tolist(),
            "per_class": per_class_metrics
        }

evaluation_harness = ModelEvaluationHarness()
