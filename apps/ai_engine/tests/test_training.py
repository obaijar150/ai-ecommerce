"""Tests for the training pipeline and the baseline-vs-model comparison."""

from __future__ import annotations

import pytest

from apps.ai_engine.ml.config import RecommenderParams, SplitParams
from apps.ai_engine.ml.data.synthetic import generate_dataset
from apps.ai_engine.ml.training.build_embedding_index import build_embedding_index
from apps.ai_engine.ml.training.train_recommender import train_recommender


def _dataset():
    return generate_dataset(n_users=60, n_items=70, interactions_per_user=10, seed=5)


def test_train_reports_baseline_and_model(artifacts_dir):
    """The report contains both models' validation and test metrics."""
    dataset = _dataset()
    report = train_recommender(
        dataset.interactions,
        dataset.items,
        params=RecommenderParams(n_components=12),
        split_params=SplitParams(seed=5),
        artifacts_dir=artifacts_dir,
    )
    assert "popularity" in report["validation"]
    assert "hybrid" in report["validation"]
    assert report["winner"] in {"hybrid", "popularity"}
    assert "ndcg@10" in report["test"]["winner"]


def test_train_records_reproducibility_metadata(artifacts_dir):
    """The saved manifest includes the seed, params and dataset fingerprint."""
    from apps.ai_engine.ml.artifacts import load_artifact

    dataset = _dataset()
    train_recommender(
        dataset.interactions,
        dataset.items,
        split_params=SplitParams(seed=5),
        artifacts_dir=artifacts_dir,
    )
    _model, metadata = load_artifact("recommender", artifacts_dir=artifacts_dir)
    assert metadata["params"]["seed"] == 5
    assert metadata["dataset_fingerprint"]
    assert metadata["kind"] == "recommender"


def test_train_is_reproducible(artifacts_dir):
    """Two runs with identical inputs produce identical metrics."""
    dataset = _dataset()
    first = train_recommender(
        dataset.interactions, dataset.items, artifacts_dir=artifacts_dir, save=False
    )
    second = train_recommender(
        dataset.interactions, dataset.items, artifacts_dir=artifacts_dir, save=False
    )
    assert first["test"] == second["test"]
    assert first["winner"] == second["winner"]


def test_train_rejects_empty_training_split(artifacts_dir):
    """An empty training split raises a clear error."""
    with pytest.raises(ValueError):
        train_recommender([], {}, artifacts_dir=artifacts_dir)


def test_build_embedding_index_reports_backend(artifacts_dir):
    """The index report records the actual backend used."""
    dataset = _dataset()
    item_ids = sorted(dataset.items)
    documents = [dataset.items[item_id]["text"] for item_id in item_ids]
    report = build_embedding_index(
        item_ids, documents, artifacts_dir=artifacts_dir
    )
    assert report["actual_backend"] == "tfidf"
    assert report["num_items"] == len(item_ids)
    assert report["artifact"]["name"] == "embedding_index"


def test_build_embedding_index_validates_lengths():
    """Mismatched item/document lengths are rejected."""
    with pytest.raises(ValueError):
        build_embedding_index(["i0"], ["a", "b"], save=False)
