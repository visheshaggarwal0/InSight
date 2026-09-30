"""theme_inference.py
Standalone MiniLM semantic theme inference engine for InSight.

Encodes incoming customer review text using the configured sentence-transformer
and computes cosine similarity against the precomputed normalized cluster
centroids, returning deterministic provisional theme assignments.

Independence of FastAPI and frontend frameworks is preserved, and so is
import-time cost: ``sentence_transformers`` is imported INSIDE the engine
constructor, never at module scope, because ``app.ml.__init__`` imports this
module and that would otherwise download ~90 MB of weights on any bare
``import app.ml`` (which ``InSight_ML/__init__.py`` performs).

Cluster count (k) and embedding width are DERIVED from the centroid artifact's
shape rather than hardcoded to 6/384, so a re-generated artifact with a
different k (e.g. 5 or 8) is scored in full instead of being rejected or
silently truncated.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

try:
    from app.ml.pipeline_config import THEME
except ImportError:  # pragma: no cover - InSight_ML shim import path
    from InSight_ML.pipeline_config import THEME

logger = logging.getLogger(__name__)

# Cosine similarities are bounded, so anything outside this is corrupt data.
_SIM_FLOOR = -1.0
_SIM_CEIL = 1.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce anything non-finite (NaN/inf) to a JSON-safe float.

    ``json.dump`` defaults to allow_nan=True, which writes the bare token
    ``NaN`` - invalid JSON that makes the browser's ``JSON.parse`` throw.
    Every float crossing this module's boundary goes through here.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(f):
        return default
    return f


class ThemeInferenceEngine:
    """
    Standalone MiniLM semantic theme inference engine for InSight.
    Encodes incoming customer review text using sentence-transformers/all-MiniLM-L6-v2,
    computes cosine similarity against the precomputed normalized cluster centroids,
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
        model_name: Optional[str] = None,
        centroids_path: Optional[str] = None,
        theme_metadata_path: Optional[str] = None,
        device: Optional[str] = None
    ):
        """
        Loads the MiniLM encoder and centroids once into memory.
        """
        self.model_name = model_name or THEME["model_name"]
        self.device = device
        self._find_base_dir()

        # 1. Resolve and load centroids
        resolved_centroids_path = centroids_path or self._resolve_path(
            "outputs/theme_detection/theme_centroids.npy"
        )
        if not os.path.exists(resolved_centroids_path):
            raise FileNotFoundError(f"Theme centroids artifact not found at: {resolved_centroids_path}")

        self.centroids = np.load(resolved_centroids_path)
        if self.centroids.ndim != 2:
            raise ValueError(
                f"Expected a 2-D (n_clusters, embedding_dim) centroid array, "
                f"but got shape {self.centroids.shape}"
            )

        # k and the embedding width come from the artifact, never from a literal.
        # A k=5 artifact used to raise ValueError, and a k=8 artifact was scored
        # against only the first 6 centroids, so argmax could never return 6/7.
        self.n_clusters, self.embedding_dim = int(self.centroids.shape[0]), int(self.centroids.shape[1])
        if self.n_clusters < 1 or self.embedding_dim < 1:
            raise ValueError(f"Degenerate centroid artifact: shape {self.centroids.shape}")
        if self.n_clusters != int(THEME["n_clusters"]):
            logger.warning(
                "Centroid artifact has k=%d but THEME['n_clusters'] is %d; using the "
                "artifact's k. Regenerate or update pipeline_config to align them.",
                self.n_clusters,
                THEME["n_clusters"],
            )
        if self.embedding_dim != int(THEME["embedding_dim"]):
            logger.warning(
                "Centroid embedding width %d differs from THEME['embedding_dim'] %d; "
                "the configured encoder may be incompatible with this artifact.",
                self.embedding_dim,
                THEME["embedding_dim"],
            )

        # Ensure centroids are normalized to unit Euclidean length.
        # np.maximum(norms, 1e-12) is NOT a guard: np.maximum(NaN, 1e-12) is NaN,
        # which then poisons every similarity downstream. Replace any
        # non-finite or near-zero norm with 1.0 (i.e. leave that row untouched)
        # and drop rows that are not finite at all.
        finite_rows = np.isfinite(self.centroids).all(axis=1)
        if not finite_rows.all():
            logger.warning(
                "Dropping %d centroid row(s) containing non-finite values.",
                int((~finite_rows).sum()),
            )
            self.centroids = self.centroids[finite_rows]

        norms = np.linalg.norm(self.centroids, axis=1, keepdims=True)
        safe_norms = np.where(np.isfinite(norms) & (norms > 1e-12), norms, 1.0)
        self.centroids = self.centroids / safe_norms
        self.n_clusters = int(self.centroids.shape[0])
        if self.n_clusters == 0:
            raise ValueError(
                f"Centroid artifact at {resolved_centroids_path} contains no usable rows."
            )

        # 2. Resolve provisional theme metadata
        self.theme_names = dict(self.DEFAULT_PROVISIONAL_THEMES)
        resolved_rep_path = theme_metadata_path or self._resolve_path(
            "outputs/theme_detection/cluster_representatives.csv"
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
                logger.warning("Could not read theme metadata %s: %s", resolved_rep_path, e)

        # Provisional names only exist for the six historical clusters; any extra
        # cluster from a re-generated artifact gets an explicit placeholder
        # instead of a KeyError.
        for cid in range(self.n_clusters):
            self.theme_names.setdefault(cid, f"Cluster {cid}")

        # 3. Load SentenceTransformer model once (imported here, not at module
        # scope, to keep `import app.ml` free of a ~90 MB download).
        t0 = time.time()
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name, device=self.device)
        except ImportError as exc:
            raise RuntimeError(
                f"sentence-transformers is not installed, so theme inference cannot run. "
                f"Install it (pip install sentence-transformers). Original error: {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load sentence embedding model '{self.model_name}'. "
                f"If you are working offline, the model must be downloaded once with an internet connection, "
                f"or run 'python scripts/download_models.py'. Original error: {exc}"
            ) from exc
        self.model_load_time_sec = round(time.time() - t0, 3)

    def _find_base_dir(self):
        """Finds project root dynamically."""
        candidates = [
            os.environ.get("INSIGHT_ROOT"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            os.getcwd(),
        ]
        self.base_dir = next((c for c in candidates if c and (os.path.exists(os.path.join(c, "outputs")) or os.path.exists(os.path.join(c, "InSight_ML")))), candidates[1])

    def _resolve_path(self, relative_path: str) -> str:
        """Resolves file path against project root candidates."""
        alt_rel = relative_path.replace("outputs", "outputs") if "outputs" in relative_path else relative_path
        candidates = [
            os.path.join(self.base_dir, relative_path),
            os.path.join(self.base_dir, alt_rel),
            os.path.join(os.getcwd(), relative_path),
            os.path.join(os.getcwd(), alt_rel),
            os.path.join("..", relative_path),
            relative_path
        ]
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        return candidates[0]

    def _unassigned(self) -> Dict[str, Any]:
        """Blank/invalid-input result, sized to the actual centroid count."""
        return {
            "predicted_cluster_id": -1,
            "provisional_theme": "Unassigned / Blank Input",
            "cosine_similarity": 0.0,
            "cluster_similarities": {c: 0.0 for c in range(self.n_clusters)},
            "cluster_similarity_by_theme": {
                self.theme_names.get(c, f"Cluster {c}"): 0.0 for c in range(self.n_clusters)
            },
            "is_provisional": True,
            "provisional_notice": "Input was blank or invalid. No theme assigned."
        }

    def _build_prediction(self, similarities: np.ndarray) -> Dict[str, Any]:
        """Turn a similarity row into a JSON-safe prediction dict.

        Every float is coerced through ``_safe_float``: a non-finite value would
        otherwise round to ``nan`` and be serialised by ``json.dump`` as the bare
        token ``NaN``, which is not valid JSON and breaks the frontend's
        ``JSON.parse``.
        """
        sims = np.where(np.isfinite(similarities), similarities, 0.0)
        pred_cid = int(np.argmax(sims))
        max_sim = _safe_float(sims[pred_cid])

        cluster_sims = {int(c): round(_safe_float(sims[c]), 4) for c in range(self.n_clusters)}
        theme_sims = {
            self.theme_names.get(int(c), f"Cluster {int(c)}"): round(_safe_float(sims[c]), 4)
            for c in range(self.n_clusters)
        }

        return {
            "predicted_cluster_id": pred_cid,
            "provisional_theme": self.theme_names.get(pred_cid, f"Cluster {pred_cid}"),
            "cosine_similarity": round(max_sim, 4),
            "cluster_similarities": cluster_sims,
            "cluster_similarity_by_theme": theme_sims,
            "is_provisional": True,
            "provisional_notice": "Provisional unsupervised theme assignment based on cosine proximity to cluster centroid."
        }

    def predict_theme(self, text: str) -> Dict[str, Any]:
        """
        Assigns a provisional theme to a single review string.

        Args:
            text: Customer review text.

        Returns:
            Dictionary containing:
                - 'predicted_cluster_id': int (0 to n_clusters-1)
                - 'provisional_theme': str
                - 'cosine_similarity': float
                - 'cluster_similarities': Dict[int, float]
                - 'cluster_similarity_by_theme': Dict[str, float]
                - 'is_provisional': bool (True)
                - 'provisional_notice': str
        """
        if not isinstance(text, str) or text.strip() == "":
            return self._unassigned()

        # Encode and normalize
        embedding = self.model.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False
        )

        # Dot product with unit centroids gives cosine similarity
        similarities = np.dot(embedding, self.centroids.T)[0]
        return self._build_prediction(similarities)

    def predict_themes_batch(self, texts: List[str], batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Assigns provisional themes across a batch of review strings.

        Args:
            texts: List of review strings.
            batch_size: Encoding batch size (defaults to THEME["batch_size"]).

        Returns:
            List of theme prediction dictionaries.
        """
        if not texts:
            return []

        if batch_size is None or batch_size <= 0:
            batch_size = int(THEME["batch_size"])

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
                results[global_idx] = self._build_prediction(sim_matrix[local_idx])

        # Populate any blank/invalid items
        for i in range(len(texts)):
            if results[i] is None:
                results[i] = self._unassigned()

        return results

_GLOBAL_ENGINE: Optional[ThemeInferenceEngine] = None


def get_theme_engine(model_name: Optional[str] = None) -> ThemeInferenceEngine:
    """Singleton getter for the ThemeInferenceEngine."""
    global _GLOBAL_ENGINE
    if _GLOBAL_ENGINE is None:
        _GLOBAL_ENGINE = ThemeInferenceEngine(model_name=model_name)
    return _GLOBAL_ENGINE


def reset_theme_engine_cache() -> None:
    """Drop the cached engine so the next get_theme_engine() rebuilds it."""
    global _GLOBAL_ENGINE
    _GLOBAL_ENGINE = None
