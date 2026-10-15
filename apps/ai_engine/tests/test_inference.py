"""Tests for inference loaders and their graceful fallbacks."""

from __future__ import annotations

from apps.ai_engine.ml.algorithms.popularity import PopularityRecommender
from apps.ai_engine.ml.artifacts import save_artifact
from apps.ai_engine.ml.data.synthetic import generate_dataset
from apps.ai_engine.ml.inference.recommender import RecommenderInference
from apps.ai_engine.ml.inference.semantic_search import SemanticSearchService


def test_recommender_falls_back_without_artifact(artifacts_dir):
    """With no trained artifact the loader serves a popularity fallback."""
    engine = RecommenderInference(artifacts_dir=artifacts_dir)
    assert engine.source == "fallback"
    assert engine.algorithm == "popularity"


def test_recommender_uses_saved_artifact(artifacts_dir):
    """A saved model is loaded and used for recommendations."""
    dataset = generate_dataset(n_users=40, n_items=50, interactions_per_user=10, seed=8)
    model = PopularityRecommender().fit(
        __import__(
            "apps.ai_engine.ml.data.dataset", fromlist=["coerce_interactions"]
        ).coerce_interactions(dataset.interactions),
        dataset.items,
    )
    save_artifact("recommender", model, {"algorithm": "popularity"}, artifacts_dir=artifacts_dir)
    engine = RecommenderInference(artifacts_dir=artifacts_dir)
    assert engine.source == "artifact"
    assert engine.algorithm == "popularity"
    assert len(engine.recommend(dataset.users[0], k=5)) == 5


def test_search_service_fits_live_index(artifacts_dir):
    """Without an artifact the search service fits a live TF-IDF index."""
    service = SemanticSearchService(
        artifacts_dir=artifacts_dir,
        live_item_ids=["i0", "i1"],
        live_documents=["wireless headphones audio", "kitchen cookbook recipes"],
    )
    assert service.source == "live"
    assert service.ready
    results = service.search("headphones", k=1)
    assert results[0][0] == "i0"


def test_search_service_unready_without_data(artifacts_dir):
    """With neither artifact nor live data the service reports not ready."""
    service = SemanticSearchService(artifacts_dir=artifacts_dir)
    assert service.ready is False
    assert service.search("anything") == []
