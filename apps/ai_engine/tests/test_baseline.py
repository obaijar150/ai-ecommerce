"""Tests for the popularity baseline."""

from __future__ import annotations

from apps.ai_engine.ml.algorithms.popularity import PopularityRecommender
from apps.ai_engine.ml.data.dataset import coerce_interactions


def _train():
    return coerce_interactions(
        [
            {"user_id": "u0", "item_id": "a", "weight": 5.0},
            {"user_id": "u0", "item_id": "b", "weight": 1.0},
            {"user_id": "u1", "item_id": "a", "weight": 2.0},
            {"user_id": "u1", "item_id": "c", "weight": 3.0},
        ]
    )


def test_baseline_ranks_by_aggregated_weight():
    """Items rank by total interaction weight."""
    model = PopularityRecommender().fit(_train())
    assert model.recommend("u0", k=3) == ["a", "c", "b"]


def test_baseline_excludes_seen_items():
    """Previously seen items are removed from recommendations."""
    model = PopularityRecommender().fit(_train())
    assert "a" not in model.recommend("u0", k=3, exclude_seen={"a"})


def test_baseline_is_identical_for_all_users():
    """The baseline is non-personalized."""
    model = PopularityRecommender().fit(_train())
    assert model.recommend("u0", 3) == model.recommend("u1", 3)


def test_baseline_scores_align_with_item_order():
    """``score`` respects the requested item order."""
    model = PopularityRecommender().fit(_train())
    assert model.score("u0", ["b", "a"]) == [1.0, 7.0]
