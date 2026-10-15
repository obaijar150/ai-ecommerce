"""
Model evaluation and comparison against the baseline.

Given a fitted model, a training split (for ``exclude_seen``) and a held-out
test split, :func:`evaluate_model` produces an aggregate report at several
cut-offs. :func:`compare_models` runs the same protocol for a set of models so
the baseline and the learned model are measured identically.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..data.dataset import Interaction
from . import metrics


def _test_relevance(test_interactions: Sequence[Interaction]) -> dict[str, set[str]]:
    """Group held-out items by user into relevance sets."""
    relevant: dict[str, set[str]] = {}
    for row in test_interactions:
        relevant.setdefault(row.user_id, set()).add(row.item_id)
    return relevant


def evaluate_model(
    model: Any,
    train_interactions: Sequence[Interaction],
    test_interactions: Sequence[Interaction],
    k_values: Sequence[int] = (5, 10),
    catalog_size: int | None = None,
) -> dict[str, Any]:
    """Evaluate ``model`` on a held-out test split.

    Args:
        model: A fitted recommender exposing ``recommend(user_id, k, exclude_seen)``.
        train_interactions: Training rows used to mask already-seen items.
        test_interactions: Held-out rows forming the relevance sets.
        k_values: Cut-offs to report.
        catalog_size: Catalog size for coverage; derived from data when omitted.

    Returns:
        A report with a ``metrics`` mapping (``metric@k -> value``), the number
        of evaluated users, and coverage.
    """
    relevant_by_user = _test_relevance(test_interactions)
    seen_by_user: dict[str, set[str]] = {}
    for row in train_interactions:
        seen_by_user.setdefault(row.user_id, set()).add(row.item_id)

    if catalog_size is None:
        catalog: set[str] = set()
        for row in list(train_interactions) + list(test_interactions):
            catalog.add(row.item_id)
        catalog_size = len(catalog)

    max_k = max(k_values)
    per_user_recommendations: dict[str, list[str]] = {}
    for user_id, relevant in relevant_by_user.items():
        if not relevant:
            continue
        per_user_recommendations[user_id] = list(
            model.recommend(user_id, k=max_k, exclude_seen=seen_by_user.get(user_id, set()))
        )

    report_metrics: dict[str, float] = {}
    for k in k_values:
        precision: list[float] = []
        recall: list[float] = []
        ndcg: list[float] = []
        average_precision: list[float] = []
        hit_rate: list[float] = []
        for user_id, relevant in relevant_by_user.items():
            recommendations = per_user_recommendations.get(user_id, [])
            if not recommendations:
                continue
            precision.append(metrics.precision_at_k(recommendations, relevant, k))
            recall.append(metrics.recall_at_k(recommendations, relevant, k))
            ndcg.append(metrics.ndcg_at_k(recommendations, relevant, k))
            average_precision.append(
                metrics.average_precision_at_k(recommendations, relevant, k)
            )
            hit_rate.append(metrics.hit_rate_at_k(recommendations, relevant, k))
        report_metrics[f"precision@{k}"] = metrics.mean(precision)
        report_metrics[f"recall@{k}"] = metrics.mean(recall)
        report_metrics[f"ndcg@{k}"] = metrics.mean(ndcg)
        report_metrics[f"map@{k}"] = metrics.mean(average_precision)
        report_metrics[f"hit_rate@{k}"] = metrics.mean(hit_rate)

    coverage = metrics.catalog_coverage(
        list(per_user_recommendations.values()), catalog_size
    )
    report_metrics["coverage"] = coverage

    return {
        "metrics": report_metrics,
        "num_users": len(per_user_recommendations),
        "catalog_size": catalog_size,
    }


def compare_models(
    models: Mapping[str, Any],
    train_interactions: Sequence[Interaction],
    test_interactions: Sequence[Interaction],
    k_values: Sequence[int] = (5, 10),
) -> dict[str, Any]:
    """Evaluate several models under an identical protocol.

    Args:
        models: Mapping ``name -> fitted model``.
        train_interactions: Training rows used for masking.
        test_interactions: Held-out rows.
        k_values: Cut-offs to report.

    Returns:
        ``{"models": {name: report}, "primary_metric": "...", "ranking": [...]}``
        where ``ranking`` is sorted best-first by the primary metric.
    """
    k_values = list(k_values)
    primary = f"ndcg@{max(k_values)}"
    reports = {
        name: evaluate_model(model, train_interactions, test_interactions, k_values)
        for name, model in models.items()
    }
    ranking = sorted(
        reports,
        key=lambda name: reports[name]["metrics"].get(primary, 0.0),
        reverse=True,
    )
    return {
        "models": reports,
        "primary_metric": primary,
        "ranking": ranking,
    }
