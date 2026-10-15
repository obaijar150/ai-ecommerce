"""
Ranking metrics for recommender evaluation.

Implemented from first principles (no external metrics library) so the numbers
are transparent and testable:

* ``precision_at_k`` — fraction of the top-k that is relevant.
* ``recall_at_k`` — fraction of relevant items recovered in the top-k.
* ``average_precision_at_k`` — rank-weighted precision (MAP when averaged).
* ``ndcg_at_k`` — normalized discounted cumulative gain (binary relevance).
* ``hit_rate_at_k`` — whether at least one relevant item is in the top-k.
"""

from __future__ import annotations

import math
from typing import Hashable, Sequence


def precision_at_k(recommended: Sequence[Hashable], relevant: set[Hashable], k: int) -> float:
    """Return precision@k, i.e. relevant hits divided by ``k``."""
    if k <= 0:
        return 0.0
    top = recommended[:k]
    hits = sum(1 for item in top if item in relevant)
    return hits / k


def recall_at_k(recommended: Sequence[Hashable], relevant: set[Hashable], k: int) -> float:
    """Return recall@k; zero when there are no relevant items."""
    if not relevant or k <= 0:
        return 0.0
    top = recommended[:k]
    hits = sum(1 for item in top if item in relevant)
    return hits / len(relevant)


def average_precision_at_k(
    recommended: Sequence[Hashable], relevant: set[Hashable], k: int
) -> float:
    """Return average precision@k over the relevant set."""
    if not relevant or k <= 0:
        return 0.0
    score = 0.0
    hits = 0
    for rank, item in enumerate(recommended[:k], start=1):
        if item in relevant:
            hits += 1
            score += hits / rank
    return score / min(len(relevant), k)


def dcg_at_k(recommended: Sequence[Hashable], relevant: set[Hashable], k: int) -> float:
    """Return discounted cumulative gain@k with binary relevance."""
    gain = 0.0
    for rank, item in enumerate(recommended[:k], start=1):
        if item in relevant:
            gain += 1.0 / math.log2(rank + 1)
    return gain


def ndcg_at_k(recommended: Sequence[Hashable], relevant: set[Hashable], k: int) -> float:
    """Return normalized DCG@k; zero when there are no relevant items."""
    if not relevant or k <= 0:
        return 0.0
    ideal_hits = min(len(relevant), k)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    if ideal == 0:
        return 0.0
    return dcg_at_k(recommended, relevant, k) / ideal


def hit_rate_at_k(recommended: Sequence[Hashable], relevant: set[Hashable], k: int) -> float:
    """Return 1.0 if any relevant item is in the top-k, else 0.0."""
    return 1.0 if any(item in relevant for item in recommended[:k]) else 0.0


def catalog_coverage(all_recommendations: Sequence[Sequence[Hashable]], catalog_size: int) -> float:
    """Return the fraction of the catalog that appears in any recommendation."""
    if catalog_size <= 0:
        return 0.0
    seen: set[Hashable] = set()
    for row in all_recommendations:
        seen.update(row)
    return len(seen) / catalog_size


def mean(values: Sequence[float]) -> float:
    """Return the arithmetic mean, or 0.0 for an empty sequence."""
    return sum(values) / len(values) if values else 0.0
