"""
Recommender inference: load the latest trained recommender and serve top-N.

The loader is resilient: if no artifact has been trained it builds an on-demand
popularity baseline from the supplied interactions, so callers always receive a
ranking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

from ..algorithms.popularity import PopularityRecommender
from ..artifacts import get_artifacts_dir, load_artifact, list_versions
from ..data.dataset import coerce_interactions


class RecommenderInference:
    """Serve recommendations from the newest trained artifact or a fallback.

    Attributes:
        model: The loaded recommender (hybrid or popularity).
        metadata: The artifact manifest, or empty when using the fallback.
        source: ``"artifact"`` or ``"fallback"``.
    """

    def __init__(
        self,
        artifact_name: str = "recommender",
        version: str | None = None,
        artifacts_dir: Path | None = None,
        fallback_interactions: Sequence[Any] | None = None,
        fallback_item_features: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        root = artifacts_dir or get_artifacts_dir()
        self.metadata: dict[str, Any] = {}
        self.source = "fallback"
        self.model: Any

        if list_versions(artifact_name, root):
            self.model, self.metadata = load_artifact(artifact_name, version, root)
            self.source = "artifact"
        else:
            baseline = PopularityRecommender()
            if fallback_interactions is not None:
                baseline.fit(
                    coerce_interactions(fallback_interactions),
                    fallback_item_features or {},
                )
            else:
                baseline.fitted = True
            self.model = baseline

    @property
    def algorithm(self) -> str:
        """Return the algorithm name of the active model."""
        if self.source == "artifact":
            return str(self.metadata.get("algorithm", getattr(self.model, "name", "unknown")))
        return getattr(self.model, "name", "popularity")

    def recommend(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: Iterable[str] | None = None,
    ) -> list[str]:
        """Return the top ``k`` item ids for ``user_id``."""
        return list(self.model.recommend(user_id, k=k, exclude_seen=exclude_seen))

    def score(self, user_id: str, item_ids: Sequence[str]) -> list[float]:
        """Return scores aligned with ``item_ids``."""
        return list(self.model.score(user_id, item_ids))
