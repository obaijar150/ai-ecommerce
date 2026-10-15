"""Tests for synthetic data generation determinism and structure."""

from __future__ import annotations

from apps.ai_engine.ml.data import synthetic


def test_generation_is_deterministic():
    """The same seed produces byte-identical datasets."""
    first = synthetic.generate_dataset(n_users=20, n_items=25, seed=123)
    second = synthetic.generate_dataset(n_users=20, n_items=25, seed=123)
    assert first.interactions == second.interactions
    assert first.items == second.items


def test_different_seeds_differ():
    """A different seed produces a different dataset."""
    first = synthetic.generate_dataset(n_users=20, n_items=25, seed=1)
    second = synthetic.generate_dataset(n_users=20, n_items=25, seed=2)
    assert first.interactions != second.interactions


def test_interactions_reference_known_items():
    """Every interaction points at a generated item."""
    dataset = synthetic.generate_dataset(n_users=10, n_items=15, seed=3)
    for row in dataset.interactions:
        assert row["item_id"] in dataset.items
        assert row["weight"] > 0
        assert row["timestamp"] >= 0


def test_every_25th_user_is_cold_start():
    """The generator deliberately leaves some users with no history."""
    dataset = synthetic.generate_dataset(n_users=50, n_items=30, seed=4)
    assert "u24" not in dataset.users


def test_item_features_include_searchable_text():
    """Items expose the fields the content model relies on."""
    items = synthetic.generate_item_features(10, seed=5)
    for item_id, feature in items.items():
        assert feature["text"]
        assert feature["category"]
        assert feature["price"] > 0
        assert item_id.startswith("i")
