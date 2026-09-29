import os
import time
from typing import List, Dict, Any, Optional, Union
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

class ThemeInferenceEngine:
    """
    Standalone MiniLM semantic theme inference engine for InSight.
    Encodes incoming customer review text using sentence-transformers/all-MiniLM-L6-v2,
    computes cosine similarity against the six precomputed normalized cluster centroids,
    and returns deterministic provisional theme assignments.

    Independent of FastAPI and frontend frameworks.
    """

    DEFAULT_PROVISIONAL_THEMES = {
        0: "Eye Care & Dark Circles",
        1: "Facial Moisturizers & Dry Skin Hydration",
        2: "Acne, Breakouts & Skin Clearing Treatments",
        3: "Lip Care & Balms",
        4: "Fragrance, Scent & Sensory Properties",
        5: "Cleansers, Face Wash & Makeup Removal"
    }

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        centroids_path: Optional[str] = None,
        theme_metadata_path: Optional[str] = None,
        device: Optional[str] = None
    ):
        """
        Loads the MiniLM encoder and centroids once into memory.
        """
        self.model_name = model_name
        self.device = device
        self._find_base_dir()

        # 1. Resolve and load centroids
        resolved_centroids_path = centroids_path or self._resolve_path(
            "InSight_ML/outputs/theme_detection/theme_centroids.npy"
        )
        if not os.path.exists(resolved_centroids_path):
            raise FileNotFoundError(f"Theme centroids artifact not found at: {resolved_centroids_path}")
        
        self.centroids = np.load(resolved_centroids_path)
        if self.centroids.ndim != 2 or self.centroids.shape != (6, 384):
            raise ValueError(f"Expected centroids shape (6, 384), but got {self.centroids.shape}")

        # Ensure centroids are normalized to unit Euclidean length
        norms = np.linalg.norm(self.centroids, axis=1, keepdims=True)
        self.centroids = self.centroids / np.maximum(norms, 1e-12)

        # 2. Resolve provisional theme metadata
        self.theme_names = dict(self.DEFAULT_PROVISIONAL_THEMES)
        resolved_rep_path = theme_metadata_path or self._resolve_path(
            "InSight_ML/outputs/theme_detection/cluster_representatives.csv"
        )
        if os.path.exists(resolved_rep_path):
            try:
                df_rep = pd.read_csv(resolved_rep_path)
                for _, row in df_rep.drop_duplicates(subset=["cluster_id"]).iterrows():
                    cid = int(row["cluster_id"])
                    if "provisional_theme" in row and pd.notna(row["provisional_theme"]):
                        self.theme_names[cid] = str(row["provisional_theme"]).strip()
            except Exception as e:
                # Fallback to defaults if metadata reading fails
                pass

        # 3. Load SentenceTransformer model once
        t0 = time.time()
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self.model_load_time_sec = round(time.time() - t0, 3)

    def _find_base_dir(self):
        """Finds project root dynamically."""
        candidates = [
            os.getcwd(),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            "/content/drive/MyDrive/InSight_ML",
            "/content"
        ]
        self.base_dir = next((c for c in candidates if os.path.exists(os.path.join(c, "InSight_ML"))), candidates[0])

    def _resolve_path(self, relative_path: str) -> str:
        """Resolves file path against project root candidates."""
        candidates = [
            os.path.join(self.base_dir, relative_path),
            os.path.join(os.getcwd(), relative_path),
            os.path.join("..", relative_path),
            relative_path
        ]
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        return candidates[0]

    def predict_theme(self, text: str) -> Dict[str, Any]:
        """
        Assigns a provisional theme to a single review string.

        Args:
            text: Customer review text.

        Returns:
            Dictionary containing:
                - 'predicted_cluster_id': int (0 to 5)
                - 'provisional_theme': str
                - 'cosine_similarity': float
                - 'cluster_similarities': Dict[int, float]
                - 'cluster_similarity_by_theme': Dict[str, float]
                - 'is_provisional': bool (True)
                - 'provisional_notice': str
        """
        if not isinstance(text, str) or text.strip() == "":
            return {
                "predicted_cluster_id": -1,
                "provisional_theme": "Unassigned / Blank Input",
                "cosine_similarity": 0.0,
                "cluster_similarities": {c: 0.0 for c in range(6)},
                "cluster_similarity_by_theme": {self.theme_names[c]: 0.0 for c in range(6)},
                "is_provisional": True,
                "provisional_notice": "Input was blank or invalid. No theme assigned."
            }

        # Encode and normalize
        embedding = self.model.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False
        )

        # Dot product with unit centroids gives cosine similarity
        similarities = np.dot(embedding, self.centroids.T)[0]
        pred_cid = int(np.argmax(similarities))
        max_sim = float(similarities[pred_cid])

        cluster_sims = {int(c): round(float(similarities[c]), 4) for c in range(6)}
        theme_sims = {self.theme_names[c]: round(float(similarities[c]), 4) for c in range(6)}

        return {
            "predicted_cluster_id": pred_cid,
            "provisional_theme": self.theme_names.get(pred_cid, f"Cluster {pred_cid}"),
            "cosine_similarity": round(max_sim, 4),
            "cluster_similarities": cluster_sims,
            "cluster_similarity_by_theme": theme_sims,
            "is_provisional": True,
            "provisional_notice": "Provisional unsupervised theme assignment based on cosine proximity to cluster centroid."
        }

    def predict_themes_batch(self, texts: List[str], batch_size: int = 64) -> List[Dict[str, Any]]:
        """
        Assigns provisional themes across a batch of review strings.

        Args:
            texts: List of review strings.
            batch_size: Encoding batch size.

        Returns:
            List of theme prediction dictionaries.
        """
        if not texts:
            return []

        # Sanitize texts for batch encoding
        valid_indices = []
        valid_texts = []
        for i, t in enumerate(texts):
            if isinstance(t, str) and t.strip():
                valid_indices.append(i)
                valid_texts.append(t)

        results = [None] * len(texts)

        if valid_texts:
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            sim_matrix = np.dot(embeddings, self.centroids.T)

            for local_idx, global_idx in enumerate(valid_indices):
                sims = sim_matrix[local_idx]
                pred_cid = int(np.argmax(sims))
                max_sim = float(sims[pred_cid])

                cluster_sims = {int(c): round(float(sims[c]), 4) for c in range(6)}
                theme_sims = {self.theme_names[c]: round(float(sims[c]), 4) for c in range(6)}

                results[global_idx] = {
                    "predicted_cluster_id": pred_cid,
                    "provisional_theme": self.theme_names.get(pred_cid, f"Cluster {pred_cid}"),
                    "cosine_similarity": round(max_sim, 4),
                    "cluster_similarities": cluster_sims,
                    "cluster_similarity_by_theme": theme_sims,
                    "is_provisional": True,
                    "provisional_notice": "Provisional unsupervised theme assignment based on cosine proximity to cluster centroid."
                }

        # Populate any blank/invalid items
        for i in range(len(texts)):
            if results[i] is None:
                results[i] = {
                    "predicted_cluster_id": -1,
                    "provisional_theme": "Unassigned / Blank Input",
                    "cosine_similarity": 0.0,
                    "cluster_similarities": {c: 0.0 for c in range(6)},
                    "cluster_similarity_by_theme": {self.theme_names[c]: 0.0 for c in range(6)},
                    "is_provisional": True,
                    "provisional_notice": "Input was blank or invalid. No theme assigned."
                }

        return results

_GLOBAL_ENGINE: Optional[ThemeInferenceEngine] = None

def get_theme_engine(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> ThemeInferenceEngine:
    """Singleton getter for the ThemeInferenceEngine."""
    global _GLOBAL_ENGINE
    if _GLOBAL_ENGINE is None:
        _GLOBAL_ENGINE = ThemeInferenceEngine(model_name=model_name)
    return _GLOBAL_ENGINE
