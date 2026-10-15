"""
Build and persist the semantic-search embedding index.

The default TF-IDF backend is fitted locally; the optional
``sentence-transformers`` backend uses the pretrained ``all-MiniLM-L6-v2`` model
as-is. The index is saved through the artifact registry together with the
backend name so inference loads a compatible model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from ..algorithms.text_embedding import build_embedding_model
from ..artifacts import fingerprint, save_artifact


def build_embedding_index(
    item_ids: Sequence[str],
    documents: Sequence[str],
    backend: str = "tfidf",
    artifact_name: str = "embedding_index",
    artifacts_dir: Path | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """Fit an embedding model over product documents and optionally save it.

    Args:
        item_ids: Item identifiers aligned with ``documents``.
        documents: Searchable text per item (name + description + attributes).
        backend: ``"tfidf"`` (default) or ``"sentence-transformers"``.
        artifact_name: Registry name for the saved index.
        artifacts_dir: Override for the artifacts root.
        save: Whether to persist the fitted index.

    Returns:
        A report with the requested/actual backend, vector count and (optionally)
        the saved artifact identifier.
    """
    if len(item_ids) != len(documents):
        raise ValueError("item_ids and documents must have the same length.")

    model = build_embedding_model(backend)
    model.fit(item_ids, documents)

    report: dict[str, Any] = {
        "requested_backend": backend,
        "actual_backend": model.backend,
        "num_items": len(item_ids),
    }

    if save:
        metadata = {
            "kind": "embedding_index",
            "backend": model.backend,
            "requested_backend": backend,
            "num_items": len(item_ids),
            "item_ids": list(item_ids),
            "dataset_fingerprint": fingerprint(list(documents)),
        }
        artifact = save_artifact(
            artifact_name, model, metadata, artifacts_dir=artifacts_dir
        )
        report["artifact"] = {"name": artifact.name, "version": artifact.version}

    return report
