"""
Management command: train and evaluate the recommender.

Trains the learned hybrid recommender and the popularity baseline on the same
split, compares them, and stores the winner. ``--source db`` uses first-party
activity data instead of the synthetic generator.

Usage:
    python manage.py ai_train_recommender
    python manage.py ai_train_recommender --source db --name recommender
    python manage.py ai_train_recommender --users 300 --items 150 --alpha 0.5
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandParser

from apps.ai_engine.ml.config import RecommenderParams, SplitParams
from apps.ai_engine.ml.data.synthetic import generate_dataset
from apps.ai_engine.ml.training.train_recommender import train_recommender


class Command(BaseCommand):
    """Train and evaluate the product recommender."""

    help = "Train the hybrid recommender and compare it against the popularity baseline."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--source",
            choices=["synthetic", "db"],
            default="synthetic",
            help="Interaction data source.",
        )
        parser.add_argument("--users", type=int, default=200)
        parser.add_argument("--items", type=int, default=120)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--components", type=int, default=32, help="SVD dimensions.")
        parser.add_argument("--alpha", type=float, default=0.6, help="Collaborative weight.")
        parser.add_argument("--name", type=str, default="recommender", help="Artifact name.")

    def handle(self, *args, **options) -> None:
        if options["source"] == "db":
            from apps.ai_engine.ml.data.django_source import (
                load_interactions_from_activity,
                load_item_features,
            )

            rows = load_interactions_from_activity()
            item_features = load_item_features()
        else:
            dataset = generate_dataset(
                n_users=options["users"],
                n_items=options["items"],
                seed=options["seed"],
            )
            rows = dataset.interactions
            item_features = dataset.items

        if not rows:
            self.stderr.write(
                self.style.WARNING("No interactions available; nothing to train.")
            )
            return

        report = train_recommender(
            rows,
            item_features,
            params=RecommenderParams(
                n_components=options["components"], alpha=options["alpha"]
            ),
            split_params=SplitParams(seed=options["seed"]),
            artifact_name=options["name"],
        )
        self.stdout.write(self.style.SUCCESS(json.dumps(report, indent=2)))
