"""
Text-embedding models for semantic product search.

Two backends share one interface so the rest of the app never cares which is
active:

* ``tfidf`` (default) — a scikit-learn TF-IDF model **fitted locally** on the
  catalog text. Deterministic, CPU-only, no downloads.
* ``sentence-transformers`` (optional) — the pretrained
  ``all-MiniLM-L6-v2`` model (Apache-2.0). It is used **as-is**; we never claim
  to have trained it. It is only attempted when the ``sentence-transformers``
  package and PyTorch are importable.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


def sentence_transformers_available() -> bool:
    """Return whether the optional sentence-transformers backend can load."""
    try:  # pragma: no cover - depends on optional install
        import sentence_transformers  # noqa: F401
    except Exception:
        return False
    return True


def torch_available() -> bool:
    """Return whether PyTorch can be imported."""
    try:  # pragma: no cover - depends on optional install
        import torch  # noqa: F401
    except Exception:
        return False
    return True


class TfidfEmbeddingModel:
    """Local TF-IDF embedding model (default, deterministic baseline).

    Attributes:
        item_ids: Item ids in row order.
        matrix: Row-normalized TF-IDF matrix (one row per item).
        backend: Always ``"tfidf"``.
    """

    backend = "tfidf"

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), sublinear_tf=True
        )
        self.item_ids: list[str] = []
        self.matrix = None
        self.fitted = False

    def fit(self, item_ids: Sequence[str], documents: Sequence[str]) -> "TfidfEmbeddingModel":
        """Fit the vectorizer and store normalized item vectors."""
        self.item_ids = list(item_ids)
        matrix = self.vectorizer.fit_transform(list(documents))
        self.matrix = normalize(matrix)
        self.fitted = True
        return self

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Encode arbitrary texts into the fitted vector space."""
        return np.asarray(normalize(self.vectorizer.transform(list(texts))).todense())

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        """Return the ``k`` most similar items to ``query``.

        Args:
            query: Free-text query.
            k: Number of results.

        Returns:
            List of ``(item_id, cosine_similarity)`` sorted descending.
        """
        if not self.fitted or self.matrix is None:
            raise RuntimeError("TfidfEmbeddingModel.fit() must be called first.")
        query_vector = normalize(self.vectorizer.transform([query]))
        similarities = np.asarray((self.matrix @ query_vector.T).todense()).ravel()
        order = np.argsort(-similarities)[:k]
        return [
            (self.item_ids[index], float(similarities[index]))
            for index in order
            if similarities[index] > 0
        ]


class SentenceTransformerEmbeddingModel:
    """Optional pretrained embedding backend (``all-MiniLM-L6-v2``)."""

    backend = "sentence-transformers"

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self.item_ids: list[str] = []
        self.matrix: np.ndarray | None = None
        self.fitted = False
        self._model: Any = None

    def _load_model(self) -> Any:
        """Lazily import and instantiate the pretrained model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # noqa: WPS433

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def fit(
        self, item_ids: Sequence[str], documents: Sequence[str]
    ) -> "SentenceTransformerEmbeddingModel":
        """Encode ``documents`` with the pretrained model."""
        model = self._load_model()
        self.item_ids = list(item_ids)
        embeddings = model.encode(list(documents), normalize_embeddings=True)
        self.matrix = np.asarray(embeddings, dtype=np.float64)
        self.fitted = True
        return self

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Encode arbitrary texts with the pretrained model."""
        model = self._load_model()
        return np.asarray(
            model.encode(list(texts), normalize_embeddings=True), dtype=np.float64
        )

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        """Return the ``k`` most similar items to ``query``."""
        if not self.fitted or self.matrix is None:
            raise RuntimeError("fit() must be called first.")
        query_vector = self.encode([query])[0]
        similarities = self.matrix @ query_vector
        order = np.argsort(-similarities)[:k]
        return [
            (self.item_ids[index], float(similarities[index])) for index in order
        ]


def build_embedding_model(backend: str = "tfidf", **kwargs: Any):
    """Factory returning an embedding model for ``backend``.

    Falls back to the TF-IDF backend when a heavy optional backend is requested
    but unavailable, so callers never crash on a missing dependency.

    Args:
        backend: ``"tfidf"`` or ``"sentence-transformers"``.
        **kwargs: Forwarded to the selected backend constructor.

    Returns:
        An embedding model instance exposing ``fit``/``encode``/``search``.
    """
    if backend in ("sentence-transformers", "sentence_transformers", "st"):
        if sentence_transformers_available() and torch_available():
            return SentenceTransformerEmbeddingModel(
                kwargs.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
            )
    return TfidfEmbeddingModel()
