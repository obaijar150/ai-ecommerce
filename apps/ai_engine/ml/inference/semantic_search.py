"""
Semantic search inference over the persisted embedding index.

Loads the newest embedding artifact. When none exists it accepts a live catalog
(``item_ids`` + ``documents``) and fits a TF-IDF index on the fly so the search
page works even before an offline build has run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from ..algorithms.text_embedding import TfidfEmbeddingModel
from ..artifacts import get_artifacts_dir, list_versions, load_artifact


class SemanticSearchService:
    """Serve semantic product search from an artifact or a live TF-IDF index.

    Attributes:
        model: The loaded or freshly fitted embedding model.
        metadata: Artifact manifest, or empty for the live fallback.
        source: ``"artifact"`` or ``"live"``.
    """

    def __init__(
        self,
        artifact_name: str = "embedding_index",
        version: str | None = None,
        artifacts_dir: Path | None = None,
        live_item_ids: Sequence[str] | None = None,
        live_documents: Sequence[str] | None = None,
    ) -> None:
        root = artifacts_dir or get_artifacts_dir()
        self.metadata: dict = {}
        self.source = "live"
        self.model = None

        if list_versions(artifact_name, root):
            self.model, self.metadata = load_artifact(artifact_name, version, root)
            self.source = "artifact"
            return

        if live_item_ids is not None and live_documents is not None:
            tfidf = TfidfEmbeddingModel()
            tfidf.fit(live_item_ids, live_documents)
            self.model = tfidf

    @property
    def ready(self) -> bool:
        """Whether a usable index is loaded."""
        return self.model is not None and getattr(self.model, "fitted", False)

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        """Return ``(item_id, score)`` pairs for ``query``.

        Returns an empty list when no index is available, so callers can fall
        back to the existing keyword search.
        """
        if not self.ready:
            return []
        return list(self.model.search(query, k=k))
