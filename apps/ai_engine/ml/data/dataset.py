"""
Dataset container, train/validation/test splitting and matrix construction.

The split is performed **per user** so every active user contributes to
training; this avoids the leakage and empty-training-user problems of a naive
global shuffle. Two strategies are supported:

* a random ratio split (``split_interactions``), and
* leave-one-out by timestamp (``leave_one_out_split``) which mirrors the
  production ranking task more closely.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from ..config import DEFAULT_SEED, SplitParams


@dataclass(frozen=True)
class Interaction:
    """A single implicit-feedback event.

    Attributes:
        user_id: User identifier.
        item_id: Item identifier.
        weight: Positive interaction strength.
        timestamp: Monotonic sort key used for temporal splits.
    """

    user_id: str
    item_id: str
    weight: float = 1.0
    timestamp: int = 0


@dataclass
class InteractionSet:
    """A named collection of interactions with convenience accessors."""

    interactions: list[Interaction]

    def __len__(self) -> int:
        return len(self.interactions)

    def __iter__(self):
        return iter(self.interactions)

    @property
    def users(self) -> list[str]:
        """Sorted, de-duplicated user identifiers."""
        return sorted({row.user_id for row in self.interactions})

    @property
    def items(self) -> list[str]:
        """Sorted, de-duplicated item identifiers."""
        return sorted({row.item_id for row in self.interactions})

    def by_user(self) -> dict[str, list[Interaction]]:
        """Group interactions by user, preserving input order."""
        grouped: dict[str, list[Interaction]] = {}
        for row in self.interactions:
            grouped.setdefault(row.user_id, []).append(row)
        return grouped

    def to_dicts(self) -> list[dict[str, Any]]:
        """Return JSON-serializable rows."""
        return [
            {
                "user_id": row.user_id,
                "item_id": row.item_id,
                "weight": row.weight,
                "timestamp": row.timestamp,
            }
            for row in self.interactions
        ]


def coerce_interactions(rows: Sequence[Any]) -> list[Interaction]:
    """Coerce dicts or :class:`Interaction` objects into ``Interaction`` rows.

    Args:
        rows: Iterable of dicts (as produced by the synthetic generator or the
            database loader) or ``Interaction`` objects.

    Returns:
        A list of ``Interaction`` objects with normalized field types.
    """
    coerced: list[Interaction] = []
    for index, row in enumerate(rows):
        if isinstance(row, Interaction):
            coerced.append(row)
            continue
        coerced.append(
            Interaction(
                user_id=str(row["user_id"]),
                item_id=str(row["item_id"]),
                weight=float(row.get("weight", 1.0)),
                timestamp=int(row.get("timestamp", index)),
            )
        )
    return coerced


def make_interaction_set(rows: Sequence[Any]) -> InteractionSet:
    """Build an :class:`InteractionSet` from raw rows."""
    return InteractionSet(interactions=coerce_interactions(rows))


def split_interactions(
    rows: Sequence[Any],
    params: SplitParams | None = None,
) -> tuple[InteractionSet, InteractionSet, InteractionSet]:
    """Split interactions per user into train/validation/test sets.

    Each user's interactions are shuffled deterministically and divided by the
    configured ratios. Users with too few interactions fall back to a
    "train must be non-empty" rule so the model always sees their history.

    Args:
        rows: Raw interaction rows.
        params: Split configuration; defaults to :class:`SplitParams`.

    Returns:
        ``(train, validation, test)`` interaction sets.
    """
    params = params or SplitParams()
    params.validate()
    rng = np.random.default_rng(params.seed)

    grouped: dict[str, list[Interaction]] = {}
    for row in coerce_interactions(rows):
        grouped.setdefault(row.user_id, []).append(row)

    train: list[Interaction] = []
    validation: list[Interaction] = []
    test: list[Interaction] = []

    for user_id in sorted(grouped):
        user_rows = list(grouped[user_id])
        order = rng.permutation(len(user_rows))
        shuffled = [user_rows[i] for i in order]
        n = len(shuffled)

        n_train = max(1, int(round(n * params.train_ratio)))
        n_val = int(round(n * params.val_ratio))
        # Guarantee at least one training row and never exceed the budget.
        n_train = min(n_train, n)
        n_val = min(n_val, n - n_train)

        train.extend(shuffled[:n_train])
        validation.extend(shuffled[n_train : n_train + n_val])
        test.extend(shuffled[n_train + n_val :])

    return (
        InteractionSet(train),
        InteractionSet(validation),
        InteractionSet(test),
    )


def leave_one_out_split(
    rows: Sequence[Any],
) -> tuple[InteractionSet, InteractionSet, InteractionSet]:
    """Temporal leave-one-out split.

    The most recent interaction per user becomes the test example, the
    second-most-recent becomes validation, and everything older is training.
    Users with a single interaction contribute it to training only.

    Args:
        rows: Raw interaction rows.

    Returns:
        ``(train, validation, test)`` interaction sets.
    """
    grouped: dict[str, list[Interaction]] = {}
    for row in coerce_interactions(rows):
        grouped.setdefault(row.user_id, []).append(row)

    train: list[Interaction] = []
    validation: list[Interaction] = []
    test: list[Interaction] = []

    for user_id in sorted(grouped):
        ordered = sorted(grouped[user_id], key=lambda row: row.timestamp)
        if len(ordered) >= 3:
            train.extend(ordered[:-2])
            validation.append(ordered[-2])
            test.append(ordered[-1])
        else:
            train.extend(ordered)

    return (
        InteractionSet(train),
        InteractionSet(validation),
        InteractionSet(test),
    )


def build_item_index(item_ids: Iterable[str]) -> dict[str, int]:
    """Return a stable ``item_id -> column`` mapping."""
    return {item_id: index for index, item_id in enumerate(sorted(set(item_ids)))}


def build_user_index(user_ids: Iterable[str]) -> dict[str, int]:
    """Return a stable ``user_id -> row`` mapping."""
    return {user_id: index for index, user_id in enumerate(sorted(set(user_ids)))}


def build_interaction_matrix(
    rows: Sequence[Interaction],
    user_index: dict[str, int],
    item_index: dict[str, int],
) -> np.ndarray:
    """Build a dense ``users x items`` weight matrix.

    Dense is fine for the dataset sizes the engine targets (hundreds of items).
    Unknown users/items are ignored so the function is safe on held-out rows.
    """
    matrix = np.zeros((len(user_index), len(item_index)), dtype=np.float64)
    for row in rows:
        if row.user_id in user_index and row.item_id in item_index:
            matrix[user_index[row.user_id], item_index[row.item_id]] += row.weight
    return matrix


def save_dataset(path: Path, dataset: dict[str, Any]) -> Path:
    """Write a dataset dictionary to ``path`` as JSON.

    Args:
        path: Destination file (parents are created).
        dataset: JSON-serializable payload.

    Returns:
        The written path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataset, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_dataset(path: Path) -> dict[str, Any]:
    """Load a dataset dictionary previously written by :func:`save_dataset`."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
