"""
Deterministic synthetic interaction-data generator.

Real interaction logs are unavailable in a fresh install, so training and
evaluation use **synthetic** data with a known latent structure. Because the
generator assigns each user and item a latent factor vector and samples
interactions from a softmax over their inner product, a matrix-factorization
model has a genuine signal to recover — a popularity baseline cannot fully
exploit it. This is what makes the baseline-vs-model comparison meaningful.

The generator is documented as synthetic (license CC0) precisely so no result
can be mistaken for real-world performance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

DEFAULT_CATEGORIES = (
    "electronics",
    "books",
    "home",
    "sports",
    "toys",
    "beauty",
    "grocery",
    "apparel",
)
DEFAULT_BRANDS = ("acme", "northwind", "globex", "initech", "umbrella", "stark")


@dataclass
class SyntheticDataset:
    """Container for a generated dataset.

    Attributes:
        interactions: List of ``{"user_id", "item_id", "weight", "timestamp"}``.
        items: ``{item_id: {"name", "text", "category", "brand", "price"}}``.
        users: Sorted list of generated user identifiers.
    """

    interactions: list[dict[str, Any]]
    items: dict[str, dict[str, Any]]
    users: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "interactions": self.interactions,
            "items": self.items,
            "users": self.users,
        }


def _softmax(values: np.ndarray) -> np.ndarray:
    """Numerically stable softmax over a 1-D array."""
    shifted = values - np.max(values)
    exp = np.exp(shifted)
    return exp / exp.sum()


def generate_item_features(
    n_items: int,
    seed: int = 42,
    categories: tuple[str, ...] = DEFAULT_CATEGORIES,
    brands: tuple[str, ...] = DEFAULT_BRANDS,
) -> dict[str, dict[str, Any]]:
    """Generate plausible catalog metadata for ``n_items`` synthetic items.

    Args:
        n_items: Number of items to create.
        seed: Random seed for reproducibility.
        categories: Category vocabulary.
        brands: Brand vocabulary.

    Returns:
        Mapping of item id to feature dictionary including a searchable text
        field built from the name, category and brand.
    """
    rng = np.random.default_rng(seed)
    items: dict[str, dict[str, Any]] = {}
    for index in range(n_items):
        item_id = f"i{index}"
        category = categories[int(rng.integers(len(categories)))]
        brand = brands[int(rng.integers(len(brands)))]
        price = float(np.round(rng.uniform(5.0, 500.0), 2))
        name = f"{brand.title()} {category.title()} Item {index}"
        text = (
            f"{name}. {brand} {category} product. "
            f"Price tier {'budget' if price < 50 else 'midrange' if price < 200 else 'premium'}."
        )
        items[item_id] = {
            "name": name,
            "text": text,
            "category": category,
            "brand": brand,
            "price": price,
        }
    return items


def generate_interactions(
    n_users: int = 200,
    n_items: int = 120,
    n_factors: int = 8,
    interactions_per_user: int = 12,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Generate implicit-feedback interactions with latent structure.

    Each user and item receive a latent factor vector; interactions are sampled
    without replacement with probability proportional to ``softmax`` of the
    inner product plus a per-item popularity bias. A small number of users are
    intentionally given no interactions to exercise the cold-start path.

    Args:
        n_users: Number of users to generate.
        n_items: Number of items to generate.
        n_factors: Latent dimensionality of the ground-truth preference model.
        interactions_per_user: Non-unique picks per user (clipped to ``n_items``).
        seed: Random seed for reproducibility.

    Returns:
        List of interaction dictionaries ordered by non-decreasing timestamp.
    """
    if interactions_per_user > n_items:
        interactions_per_user = n_items

    rng = np.random.default_rng(seed)
    user_factors = rng.normal(size=(n_users, n_factors))
    item_factors = rng.normal(size=(n_items, n_factors))
    item_bias = rng.normal(scale=0.4, size=n_items)

    interactions: list[dict[str, Any]] = []
    timestamp = 0
    for user_index in range(n_users):
        # Every 25th user is a cold-start user with no history.
        if user_index % 25 == 24:
            continue
        scores = user_factors[user_index] @ item_factors.T + item_bias
        probabilities = _softmax(scores)
        chosen = rng.choice(
            n_items, size=interactions_per_user, replace=False, p=probabilities
        )
        for item_index in chosen:
            timestamp += 1
            weight = float(np.round(1.0 + max(scores[item_index], 0.0), 4))
            interactions.append(
                {
                    "user_id": f"u{user_index}",
                    "item_id": f"i{int(item_index)}",
                    "weight": weight,
                    "timestamp": timestamp,
                }
            )
    return interactions


def generate_dataset(
    n_users: int = 200,
    n_items: int = 120,
    n_factors: int = 8,
    interactions_per_user: int = 12,
    seed: int = 42,
) -> SyntheticDataset:
    """Generate a complete synthetic dataset (interactions + item features).

    The same ``seed`` is used for both items and interactions so the whole
    dataset is reproducible from a single number.
    """
    items = generate_item_features(n_items, seed=seed)
    interactions = generate_interactions(
        n_users=n_users,
        n_items=n_items,
        n_factors=n_factors,
        interactions_per_user=interactions_per_user,
        seed=seed,
    )
    users = sorted({row["user_id"] for row in interactions})
    return SyntheticDataset(interactions=interactions, items=items, users=users)
