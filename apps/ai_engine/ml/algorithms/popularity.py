"""
Popularity baseline recommender.

This is the deterministic reference every learned model must beat. It ranks
items by aggregated interaction weight from the training split and needs no
per-user information, so it also serves as the cold-start fallback.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Sequence

from ..data.dataset import Interaction


class PopularityRecommender:
    """Non-personalized "most interacted" baseline.

    Attributes:
        item_scores: Mapping of item id to aggregated weight.
        ranked_items: Item ids sorted by descending score then id.
        fitted: Whether :meth:`fit` has been called.
    """

    name = "popularity"

    def __init__(self) -> None:
        self.item_scores: dict[str, float] = {}
        self.ranked_items: list[str] = []
        self.fitted = False

    def fit(
        self,
        interactions: Sequence[Interaction],
        item_features: dict[str, dict[str, Any]] | None = None,
    ) -> "PopularityRecommender":
        """Compute item popularity from training interactions.

        Args:
            interactions: Training interactions.
            item_features: Unused; accepted for interface compatibility.

        Returns:
            ``self`` to allow fluent chaining.
        """
        scores: dict[str, float] = defaultdict(float)
        for row in interactions:
            scores[row.item_id] += row.weight
        self.item_scores = dict(scores)
        self.ranked_items = [
            item_id
            for item_id, _ in sorted(
                self.item_scores.items(), key=lambda kv: (-kv[1], kv[0])
            )
        ]
        self.fitted = True
        return self

    def recommend(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: Iterable[str] | None = None,
    ) -> list[str]:
        """Return the ``k`` most popular items, skipping ``exclude_seen``."""
        seen = set(exclude_seen or ())
        results: list[str] = []
        for item_id in self.ranked_items:
            if item_id in seen:
                continue
            results.append(item_id)
            if len(results) >= k:
                break
        return results

    def score(self, user_id: str, item_ids: Sequence[str]) -> list[float]:
        """Return popularity scores aligned with ``item_ids``."""
        return [float(self.item_scores.get(item_id, 0.0)) for item_id in item_ids]
