"""Tests for dataset splitting, indexing and persistence."""

from __future__ import annotations

import pytest

from apps.ai_engine.ml.config import SplitParams
from apps.ai_engine.ml.data import dataset as ds


def _rows(users: int = 6, per_user: int = 10) -> list[dict]:
    rows = []
    timestamp = 0
    for user in range(users):
        for index in range(per_user):
            timestamp += 1
            rows.append(
                {
                    "user_id": f"u{user}",
                    "item_id": f"i{index}",
                    "weight": 1.0,
                    "timestamp": timestamp,
                }
            )
    return rows


def test_split_is_deterministic():
    """The same params yield identical splits."""
    params = SplitParams(seed=11)
    first = ds.split_interactions(_rows(), params)
    second = ds.split_interactions(_rows(), params)
    assert [r.user_id for r in first[0]] == [r.user_id for r in second[0]]
    assert first[2].to_dicts() == second[2].to_dicts()


def test_split_keeps_every_user_in_training():
    """Per-user splitting guarantees each user appears in the training set."""
    train, _val, _test = ds.split_interactions(_rows())
    assert set(train.users) == {"u0", "u1", "u2", "u3", "u4", "u5"}


def test_split_ratios_partition_all_interactions():
    """No interaction is lost or duplicated across the three sets."""
    rows = _rows()
    train, val, test = ds.split_interactions(rows)
    assert len(train) + len(val) + len(test) == len(rows)


def test_invalid_split_ratios_raise():
    """Ratios that do not sum to 1.0 are rejected."""
    with pytest.raises(ValueError):
        ds.SplitParams(train_ratio=0.5, val_ratio=0.2, test_ratio=0.2).validate()


def test_leave_one_out_orders_by_timestamp():
    """Leave-one-out puts the newest row in test and the next in validation."""
    train, val, test = ds.leave_one_out_split(_rows(users=1, per_user=5))
    assert test.interactions[0].timestamp > val.interactions[0].timestamp
    assert len(train) == 3


def test_leave_one_out_handles_sparse_users():
    """Users with fewer than three rows contribute to training only."""
    rows = [
        {"user_id": "u0", "item_id": "i0", "timestamp": 1},
        {"user_id": "u0", "item_id": "i1", "timestamp": 2},
    ]
    train, val, test = ds.leave_one_out_split(rows)
    assert len(train) == 2
    assert len(val) == 0 and len(test) == 0


def test_build_interaction_matrix_aggregates_weights():
    """Repeated pairs are summed in the interaction matrix."""
    rows = ds.coerce_interactions(
        [
            {"user_id": "u0", "item_id": "i0", "weight": 1.0},
            {"user_id": "u0", "item_id": "i0", "weight": 2.0},
        ]
    )
    user_index = ds.build_user_index([r.user_id for r in rows])
    item_index = ds.build_item_index([r.item_id for r in rows])
    matrix = ds.build_interaction_matrix(rows, user_index, item_index)
    assert matrix[0, 0] == 3.0


def test_matrix_ignores_unknown_ids():
    """Unknown ids in held-out rows do not raise or corrupt the matrix."""
    rows = ds.coerce_interactions([{"user_id": "u9", "item_id": "i9"}])
    matrix = ds.build_interaction_matrix(rows, {}, {})
    assert matrix.shape == (0, 0)


def test_dataset_round_trip(tmp_path):
    """Datasets survive a JSON save/load round trip."""
    payload = {"interactions": _rows(users=1, per_user=2), "items": {"i0": {"text": "x"}}}
    path = ds.save_dataset(tmp_path / "ds.json", payload)
    assert ds.load_dataset(path) == payload


def test_interaction_set_accessors():
    """InteractionSet exposes sorted users/items and grouping."""
    rows = ds.coerce_interactions(_rows(users=2, per_user=3))
    interaction_set = ds.InteractionSet(rows)
    assert interaction_set.users == ["u0", "u1"]
    assert interaction_set.items == ["i0", "i1", "i2"]
    assert len(interaction_set.by_user()["u0"]) == 3
