"""
Management command: evaluate the latest trained recommender.

Re-derives the deterministic synthetic split and reports precision/recall/NDCG
for both the saved model and the popularity baseline so the two are always
compared side by side.

Usage:
    python manage.py ai_evaluate_recommender
    python manage.py ai_evaluate_recommender --users 300 --items 150
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandParser

from apps.ai_engine.ml.config import EVAL_K_VALUES, SplitParams
from apps.ai_engine.ml.data.synthetic import generate_dataset
from apps.ai_engine.ml.data.dataset import split_interactions
from apps.ai_engine.ml.algorithms.popularity import PopularityRecommender
from apps.ai_engine.ml.artifacts import latest_version, load_artifact, list_versions
from apps.ai_engine.ml.evaluation.evaluate_recommender import evaluate_model


class Command(BaseCommand):
    """Evaluate the saved recommender and the baseline on the same test split."""

    help = "Evaluate the latest recommender artifact and the popularity baseline."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--users", type=int, default=200)
        parser.add_argument("--items", type=int, default=120)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--name", type=str, default="recommender")

    def handle(self, *args, **options) -> None:
        dataset = generate_dataset(
            n_users=options["users"],
            n_items=options["items"],
            seed=options["seed"],
        )
        train, _validation, test = split_interactions(
            dataset.interactions, SplitParams(seed=options["seed"])
        )

        baseline = PopularityRecommender().fit(train.interactions, dataset.items)
        baseline_report = evaluate_model(
            baseline, train.interactions, test.interactions, EVAL_K_VALUES
        )

        result: dict = {"name": options["name"], "baseline": baseline_report["metrics"]}

        if list_versions(options["name"]):
            model, metadata = load_artifact(options["name"])
            model_report = evaluate_model(
                model, train.interactions, test.interactions, EVAL_K_VALUES
            )
            result["artifact"] = {
                "version": latest_version(options["name"]),
                "algorithm": metadata.get("algorithm", "unknown"),
                "metrics": model_report["metrics"],
            }
        else:
            self.stderr.write(
                self.style.WARNING(
                    "No recommender artifact found; run ai_train_recommender first."
                )
            )

        self.stdout.write(self.style.SUCCESS(json.dumps(result, indent=2)))
