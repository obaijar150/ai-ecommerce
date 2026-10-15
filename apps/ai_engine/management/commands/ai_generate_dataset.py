"""
Management command: generate a reproducible synthetic interaction dataset.

Usage:
    python manage.py ai_generate_dataset
    python manage.py ai_generate_dataset --users 300 --items 150 --out ai_artifacts/dataset.json
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from apps.ai_engine.ml.config import get_artifacts_dir
from apps.ai_engine.ml.data.dataset import save_dataset
from apps.ai_engine.ml.data.synthetic import generate_dataset


class Command(BaseCommand):
    """Generate a deterministic synthetic dataset for training/evaluation."""

    help = "Generate a deterministic synthetic interaction dataset (no real data)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--users", type=int, default=200, help="Number of users.")
        parser.add_argument("--items", type=int, default=120, help="Number of items.")
        parser.add_argument("--seed", type=int, default=42, help="Random seed.")
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output JSON path (defaults to <artifacts>/datasets/synthetic.json).",
        )

    def handle(self, *args, **options) -> None:
        dataset = generate_dataset(
            n_users=options["users"],
            n_items=options["items"],
            seed=options["seed"],
        )
        out = (
            Path(options["out"])
            if options["out"]
            else get_artifacts_dir() / "datasets" / "synthetic.json"
        )
        save_dataset(out, dataset.to_dict())
        self.stdout.write(
            self.style.SUCCESS(
                json.dumps(
                    {
                        "path": str(out),
                        "interactions": len(dataset.interactions),
                        "items": len(dataset.items),
                        "users": len(dataset.users),
                        "seed": options["seed"],
                    },
                    indent=2,
                )
            )
        )
