"""Tests for ranking metrics."""

from __future__ import annotations

import math

from apps.ai_engine.ml.evaluation import metrics


def test_precision_at_k_counts_hits():
    """Precision@k is the number of relevant items divided by k."""
    assert metrics.precision_at_k(["a", "b", "c"], {"a", "c"}, 3) == 2 / 3
    assert metrics.precision_at_k(["a", "b", "c"], {"a", "c"}, 1) == 1.0


def test_recall_at_k_uses_relevant_set_size():
    """Recall@k is hits divided by the number of relevant items."""
    assert metrics.recall_at_k(["a", "b"], {"a", "b", "c"}, 2) == 2 / 3
    assert metrics.recall_at_k(["a"], {"a", "b", "c"}, 1) == 1 / 3


def test_recall_is_zero_without_relevant_items():
    """An empty relevance set yields zero recall and NDCG."""
    assert metrics.recall_at_k(["a"], set(), 5) == 0.0
    assert metrics.ndcg_at_k(["a"], set(), 5) == 0.0


def test_ndcg_rewards_earlier_hits():
    """A hit at rank 1 scores higher than the same hit at rank 3."""
    relevant = {"a"}
    assert metrics.ndcg_at_k(["a", "x", "y"], relevant, 3) == 1.0
    early = metrics.ndcg_at_k(["x", "a", "y"], relevant, 3)
    late = metrics.ndcg_at_k(["x", "y", "a"], relevant, 3)
    assert early > late


def test_ndcg_matches_closed_form():
    """NDCG for a single relevant item at rank 2 matches the formula."""
    relevant = {"a"}
    expected = (1.0 / math.log2(3)) / (1.0 / math.log2(2))
    assert metrics.ndcg_at_k(["x", "a"], relevant, 2) == expected


def test_average_precision_weights_rank():
    """Average precision favours relevant items near the top."""
    relevant = {"a", "b"}
    assert metrics.average_precision_at_k(["a", "b"], relevant, 2) == 1.0
    assert metrics.average_precision_at_k(["x", "a", "b"], relevant, 3) < 1.0


def test_hit_rate_at_k():
    """Hit rate is 1 when any relevant item appears in the top-k."""
    assert metrics.hit_rate_at_k(["x", "a"], {"a"}, 2) == 1.0
    assert metrics.hit_rate_at_k(["x", "y"], {"a"}, 2) == 0.0


def test_catalog_coverage():
    """Coverage is the fraction of the catalog that was recommended."""
    assert metrics.catalog_coverage([["a", "b"], ["c"]], 4) == 0.75
    assert metrics.catalog_coverage([], 0) == 0.0


def test_mean_handles_empty_input():
    """``mean`` returns 0.0 for empty input."""
    assert metrics.mean([]) == 0.0
    assert metrics.mean([1.0, 3.0]) == 2.0
