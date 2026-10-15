"""Tests for the learned hybrid recommender (ranking, cold start, determinism)."""

from __future__ import annotations

import numpy as np

from apps.ai_engine.ml.algorithms.hybrid_recommender import HybridRecommender
from apps.ai_engine.ml.config import RecommenderParams
from apps.ai_engine.ml.data.dataset import coerce_interactions
from apps.ai_engine.ml.data.synthetic import generate_dataset


def _fit_synthetic():
    dataset = generate_dataset(n_users=40, n_items=50, interactions_per_user=10, seed=9)
    model = HybridRecommender(RecommenderParams(n_components=8, alpha=0.6)).fit(
        coerce_interactions(dataset.interactions), dataset.items
    )
    return dataset, model


def test_fit_learns_factors():
    """Fitting produces latent factors sized to the data."""
    _dataset, model = _fit_synthetic()
    assert model.fitted
    assert model.user_factors is not None
    assert model.item_factors is not None
    assert model.user_factors.shape[0] == len(model.user_index)
    assert model.item_factors.shape[0] == len(model.item_index)


def test_recommend_returns_distinct_items():
    """Recommendations are unique and respect the requested count."""
    dataset, model = _fit_synthetic()
    user = dataset.users[0]
    recs = model.recommend(user, k=10)
    assert len(recs) == 10
    assert len(set(recs)) == 10


def test_recommend_excludes_seen_by_default():
    """A user's own history is never recommended back to them."""
    dataset, model = _fit_synthetic()
    user = dataset.users[0]
    recs = model.recommend(user, k=10)
    assert not (set(recs) & model.seen[user])


def test_cold_start_user_gets_popular_items():
    """An unknown user receives a popularity-ranked list, never an error."""
    dataset, model = _fit_synthetic()
    recs = model.recommend("brand-new-user", k=5)
    assert len(recs) == 5
    assert recs == model.popularity[:5]


def test_scores_align_with_requested_items():
    """``score`` returns one float per requested item."""
    dataset, model = _fit_synthetic()
    user = dataset.users[0]
    items = list(model.item_ids)[:5]
    scores = model.score(user, items)
    assert len(scores) == 5
    assert all(isinstance(score, float) for score in scores)


def test_model_beats_baseline_or_matches_on_synthetic_data():
    """On the latent-factor data the learned model is not worse than popularity.

    The synthetic data is generated from a latent-factor model, so a
    factorization recommender should recover that structure and score at least
    as well as a non-personalized baseline on held-out interactions. This is a
    property of the *synthetic* data only and is not a real-world claim.
    """
    from apps.ai_engine.ml.algorithms.popularity import PopularityRecommender
    from apps.ai_engine.ml.config import EVAL_K_VALUES
    from apps.ai_engine.ml.data.dataset import split_interactions
    from apps.ai_engine.ml.evaluation.evaluate_recommender import evaluate_model

    dataset = generate_dataset(n_users=80, n_items=80, interactions_per_user=12, seed=21)
    train, _val, test = split_interactions(dataset.interactions)

    baseline = PopularityRecommender().fit(train.interactions, dataset.items)
    hybrid = HybridRecommender(RecommenderParams(n_components=16, alpha=0.6)).fit(
        train.interactions, dataset.items
    )

    baseline_report = evaluate_model(
        baseline, train.interactions, test.interactions, EVAL_K_VALUES
    )
    hybrid_report = evaluate_model(
        hybrid, train.interactions, test.interactions, EVAL_K_VALUES
    )
    assert (
        hybrid_report["metrics"]["ndcg@10"] >= baseline_report["metrics"]["ndcg@10"]
    )


def test_fit_is_deterministic():
    """Fitting twice on the same data yields identical recommendations."""
    dataset = generate_dataset(n_users=20, n_items=30, interactions_per_user=8, seed=31)
    rows = coerce_interactions(dataset.interactions)
    first = HybridRecommender(RecommenderParams(n_components=6)).fit(rows, dataset.items)
    second = HybridRecommender(RecommenderParams(n_components=6)).fit(rows, dataset.items)
    assert first.recommend("u0", 10) == second.recommend("u0", 10)


def test_unfitted_model_raises_on_recommend():
    """Calling recommend before fit is a clear error."""
    model = HybridRecommender()
    try:
        model.recommend("u0")
    except RuntimeError as exc:
        assert "fit" in str(exc).lower()
    else:  # pragma: no cover
        raise AssertionError("Expected RuntimeError")


def test_degenerate_single_item_dataset():
    """A one-item / one-user dataset does not crash fitting."""
    rows = coerce_interactions([{"user_id": "u0", "item_id": "i0", "weight": 1.0}])
    model = HybridRecommender().fit(rows, {"i0": {"text": "only item"}})
    assert model.fitted
    assert isinstance(model.item_factors, np.ndarray)
