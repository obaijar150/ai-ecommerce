"""
Train and evaluate the recommender, comparing it against the baseline.

The pipeline is fully reproducible: a single seed drives dataset generation and
the train/validation/test split, and *both* models are evaluated with the same
protocol. The learned model is only promoted to ``latest`` if it matches or
beats the baseline on validation NDCG; otherwise the baseline is saved. This
prevents the common fallacy of shipping a worse model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from ..artifacts import fingerprint, save_artifact
from ..algorithms.hybrid_recommender import HybridRecommender
from ..algorithms.popularity import PopularityRecommender
from ..config import EVAL_K_VALUES, RecommenderParams, SplitParams
from ..data.dataset import Interaction, make_interaction_set, split_interactions
from ..evaluation.evaluate_recommender import evaluate_model


def _select_primary(report: dict[str, Any]) -> float:
    """Return the primary comparison metric (NDCG at the largest cut-off)."""
    key = f"ndcg@{max(EVAL_K_VALUES)}"
    return float(report["metrics"].get(key, 0.0))


def train_recommender(
    rows: Sequence[Any],
    item_features: dict[str, dict[str, Any]],
    params: RecommenderParams | None = None,
    split_params: SplitParams | None = None,
    artifact_name: str = "recommender",
    artifacts_dir: Path | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """Train the hybrid recommender and compare it to the popularity baseline.

    Args:
        rows: Raw interaction rows (dicts or ``Interaction`` objects).
        item_features: ``{item_id: {"text": ...}}`` used by the content model.
        params: Recommender hyper-parameters.
        split_params: Split configuration.
        artifact_name: Registry name for the saved artifact.
        artifacts_dir: Override for the artifacts root.
        save: Whether to persist the winning model.

    Returns:
        A report containing the split sizes, both evaluation reports, the
        chosen model name and (optionally) the saved artifact identifier.

    Raises:
        ValueError: If the training split has no interactions.
    """
    params = params or RecommenderParams()
    split_params = split_params or SplitParams()

    train, validation, test = split_interactions(rows, split_params)
    if len(train) == 0:
        raise ValueError("Training split is empty; provide more interactions.")

    # Fit both models on the training split.
    baseline = PopularityRecommender().fit(train.interactions, item_features)
    hybrid = HybridRecommender(params).fit(train.interactions, item_features)

    # Validate to pick the winner.
    baseline_val = evaluate_model(
        baseline, train.interactions, validation.interactions, EVAL_K_VALUES
    )
    hybrid_val = evaluate_model(
        hybrid, train.interactions, validation.interactions, EVAL_K_VALUES
    )

    baseline_score = _select_primary(baseline_val)
    hybrid_score = _select_primary(hybrid_val)
    winner_name = "hybrid" if hybrid_score >= baseline_score else "popularity"
    winner = hybrid if winner_name == "hybrid" else baseline

    # Final honest report on the untouched test split.
    test_report = evaluate_model(
        winner, train.interactions, test.interactions, EVAL_K_VALUES
    )
    baseline_test = evaluate_model(
        baseline, train.interactions, test.interactions, EVAL_K_VALUES
    )

    report: dict[str, Any] = {
        "split": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
            "users": len(train.users),
            "items": len(train.items),
        },
        "params": {
            "n_components": params.n_components,
            "alpha": params.alpha,
            "top_k": params.top_k,
            "seed": split_params.seed,
        },
        "validation": {
            "popularity": baseline_val["metrics"],
            "hybrid": hybrid_val["metrics"],
        },
        "test": {
            "winner": test_report["metrics"],
            "popularity_baseline": baseline_test["metrics"],
        },
        "winner": winner_name,
    }

    if save:
        metadata = {
            "kind": "recommender",
            "algorithm": winner_name,
            "params": report["params"],
            "split": report["split"],
            "validation_metrics": report["validation"],
            "test_metrics": report["test"],
            "winner": winner_name,
            "dataset_fingerprint": fingerprint(
                [row.to_dicts() if hasattr(row, "to_dicts") else row for row in rows]
            ),
            "item_features_count": len(item_features),
        }
        artifact = save_artifact(
            artifact_name, winner, metadata, artifacts_dir=artifacts_dir
        )
        report["artifact"] = {"name": artifact.name, "version": artifact.version}
        report["selected_model"] = winner_name

    return report
