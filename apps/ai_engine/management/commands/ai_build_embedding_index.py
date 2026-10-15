"""
Management command: rebuild the semantic-search embedding index.

By default the local TF-IDF backend is used. Requesting the optional
``sentence-transformers`` backend silently falls back to TF-IDF when the heavy
dependency is not installed, and the report records which backend actually ran.

Usage:
    python manage.py ai_build_embedding_index
    python manage.py ai_build_embedding_index --source db
    python manage.py ai_build_embedding_index --backend sentence-transformers
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandParser

from apps.ai_engine.ml.config import get_artifacts_dir
from apps.ai_engine.ml.data.synthetic import generate_dataset
from apps.ai_engine.ml.training.build_embedding_index import build_embedding_index


class Command(BaseCommand):
    """Build and persist the embedding index used for semantic search."""

    help = "Build the semantic-search embedding index (TF-IDF by default)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--source",
            choices=["synthetic", "db"],
            default="synthetic",
            help="Product text source.",
        )
        parser.add_argument(
            "--backend",
            choices=["tfidf", "sentence-transformers"],
            default="tfidf",
            help="Embedding backend; optional heavy backend falls back to TF-IDF.",
        )
        parser.add_argument("--items", type=int, default=120, help="Synthetic item count.")
        parser.add_argument(
            "--name", type=str, default="embedding_index", help="Artifact name."
        )

    def handle(self, *args, **options) -> None:
        if options["source"] == "db":
            from apps.ai_engine.ml.data.django_source import load_item_features

            features = load_item_features()
            item_ids = sorted(features)
            documents = [features[item_id]["text"] for item_id in item_ids]
        else:
            dataset = generate_dataset(n_items=options["items"])
            item_ids = sorted(dataset.items)
            documents = [dataset.items[item_id]["text"] for item_id in item_ids]

        if not item_ids:
            self.stderr.write(
                self.style.WARNING("No products found; nothing to index.")
            )
            return

        report = build_embedding_index(
            item_ids,
            documents,
            backend=options["backend"],
            artifact_name=options["name"],
            artifacts_dir=get_artifacts_dir(),
        )
        self.stdout.write(self.style.SUCCESS(json.dumps(report, indent=2)))
