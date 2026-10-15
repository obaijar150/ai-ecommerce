"""
Hybrid recommender: truncated-SVD collaborative filtering blended with a
TF-IDF content model.

This is the **learned** model the engine trains. Nothing here is pretrained:
the SVD factors and the content vectorizer are fitted from scratch on the
supplied interaction data and item text. ``alpha`` controls the blend between
the collaborative signal and the content signal.

For a user with no history (cold start) the model falls back to item popularity
derived from the training split, so inference never fails.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Sequence

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from ..config import RecommenderParams
from ..data.dataset import (
    Interaction,
    build_interaction_matrix,
    build_item_index,
    build_user_index,
)


def _minmax(values: np.ndarray) -> np.ndarray:
    """Scale an array to ``[0, 1]``; returns zeros for a constant array."""
    if values.size == 0:
        return values
    low = float(np.min(values))
    high = float(np.max(values))
    if high - low < 1e-12:
        return np.zeros_like(values)
    return (values - low) / (high - low)


class HybridRecommender:
    """Collaborative + content hybrid recommender.

    Attributes:
        params: Hyper-parameters used to fit the model.
        user_index: Mapping of user id to matrix row.
        item_index: Mapping of item id to matrix column.
        item_ids: Item ids ordered by column index.
        item_factors: Learned item latent vectors (from SVD).
        user_factors: Learned user latent vectors (from SVD).
        popularity: Training-split popularity used as a cold-start fallback.
        fitted: Whether :meth:`fit` has been called.
    """

    name = "hybrid"

    def __init__(self, params: RecommenderParams | None = None) -> None:
        self.params = params or RecommenderParams()
        self.user_index: dict[str, int] = {}
        self.item_index: dict[str, int] = {}
        self.item_ids: list[str] = []
        self.item_factors: np.ndarray | None = None
        self.user_factors: np.ndarray | None = None
        self.item_content: np.ndarray | None = None
        self.seen: dict[str, set[str]] = {}
        self.popularity: list[str] = []
        self._popularity_scores: dict[str, float] = {}
        self.fitted = False

    # -- training ---------------------------------------------------------
    def fit(
        self,
        interactions: Sequence[Interaction],
        item_features: dict[str, dict[str, Any]] | None = None,
    ) -> "HybridRecommender":
        """Fit the collaborative and content components.

        Args:
            interactions: Training interactions (after any filtering).
            item_features: Mapping ``item_id -> {"text": ...}`` used to build
                the content model. Missing text yields an empty document.

        Returns:
            ``self`` for fluent chaining.
        """
        item_features = item_features or {}
        rows = list(interactions)
        self.user_index = build_user_index(row.user_id for row in rows)
        self.item_index = build_item_index(row.item_id for row in rows)
        self.item_ids = [
            item_id
            for item_id, _ in sorted(self.item_index.items(), key=lambda kv: kv[1])
        ]
        self.seen = defaultdict(set)  # type: ignore[assignment]
        for row in rows:
            self.seen.setdefault(row.user_id, set()).add(row.item_id)

        matrix = build_interaction_matrix(rows, self.user_index, self.item_index)

        n_users, n_items = matrix.shape
        # SVD requires components < min(shape) and at least 1 row/column.
        max_components = max(1, min(n_users, n_items) - 1)
        n_components = int(min(self.params.n_components, max_components))
        if n_users >= 1 and n_items >= 2:
            svd = TruncatedSVD(n_components=n_components, random_state=0)
            self.user_factors = svd.fit_transform(matrix)
            self.item_factors = svd.components_.T
        else:  # pragma: no cover - degenerate tiny datasets
            self.user_factors = np.zeros((n_users, 1))
            self.item_factors = np.zeros((n_items, 1))

        # Content model over item text.
        documents = [
            str(item_features.get(item_id, {}).get("text", item_id))
            for item_id in self.item_ids
        ]
        if documents and any(doc.strip() for doc in documents):
            vectorizer = TfidfVectorizer(stop_words="english")
            content = vectorizer.fit_transform(documents)
            self.item_content = normalize(content)
        else:  # pragma: no cover - handled by tests with real features
            self.item_content = None

        # Popularity fallback.
        weights: dict[str, float] = defaultdict(float)
        for row in rows:
            weights[row.item_id] += row.weight
        self._popularity_scores = dict(weights)
        self.popularity = [
            item_id
            for item_id, _ in sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

        self.fitted = True
        return self

    # -- scoring ----------------------------------------------------------
    def _collaborative_scores(self, user_id: str) -> np.ndarray:
        """Return a raw collaborative score per item for ``user_id``."""
        assert self.item_factors is not None and self.user_factors is not None
        if user_id in self.user_index:
            user_vector = self.user_factors[self.user_index[user_id]]
            return self.item_factors @ user_vector
        return np.zeros(len(self.item_ids))

    def _content_scores(self, user_id: str) -> np.ndarray:
        """Return a raw content-similarity score per item for ``user_id``."""
        if self.item_content is None or user_id not in self.seen:
            return np.zeros(len(self.item_ids))
        seen_items = self.seen[user_id]
        rows = [
            self.item_index[item_id]
            for item_id in seen_items
            if item_id in self.item_index
        ]
        if not rows:
            return np.zeros(len(self.item_ids))
        profile = np.asarray(self.item_content[rows].mean(axis=0))
        return np.asarray(self.item_content @ profile.T).ravel()

    def _blended_scores(self, user_id: str) -> np.ndarray:
        """Blend collaborative and content scores into ``[0, 1]``."""
        collaborative = _minmax(self._collaborative_scores(user_id))
        content = _minmax(self._content_scores(user_id))
        alpha = self.params.alpha
        if self.item_content is None:
            return collaborative
        return alpha * collaborative + (1.0 - alpha) * content

    def score(self, user_id: str, item_ids: Sequence[str]) -> list[float]:
        """Return blended scores for specific ``item_ids``.

        A user with no history receives popularity-derived scores so the
        function always returns a meaningful, comparable ranking.
        """
        if user_id in self.user_index:
            blended = self._blended_scores(user_id)
            return [
                float(blended[self.item_index[item_id]])
                if item_id in self.item_index
                else 0.0
                for item_id in item_ids
            ]
        popularity_rank = {item_id: index for index, item_id in enumerate(self.popularity)}
        total = max(1, len(popularity_rank))
        return [
            1.0 - popularity_rank.get(item_id, total) / total for item_id in item_ids
        ]

    def recommend(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: Iterable[str] | None = None,
    ) -> list[str]:
        """Return the top ``k`` items for ``user_id``.

        Args:
            user_id: Target user.
            k: Number of recommendations.
            exclude_seen: Extra items to exclude (usually the user's history).
        """
        if not self.fitted:
            raise RuntimeError("HybridRecommender.fit() must be called first.")

        if user_id in self.user_index:
            blended = self._blended_scores(user_id)
        else:
            # Cold start: derive scores purely from popularity.
            blended = np.array(
                [self._popularity_scores.get(item_id, 0.0) for item_id in self.item_ids]
            )

        excluded = set(exclude_seen or ())
        excluded |= self.seen.get(user_id, set())

        ranked: list[tuple[str, float]] = []
        for index, item_id in enumerate(self.item_ids):
            if item_id in excluded:
                continue
            ranked.append((item_id, float(blended[index])))
        ranked.sort(key=lambda pair: (-pair[1], pair[0]))
        return [item_id for item_id, _ in ranked[:k]]
