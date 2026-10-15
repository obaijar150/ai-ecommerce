"""
Management command: summarize text (reviews) with graceful fallback.

Usage:
    python manage.py ai_summarize --text "Great product. Battery lasts. Cheap."
    python manage.py ai_summarize --file reviews.txt --backend extractive
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from apps.ai_engine.ml.algorithms.summarizer import build_summarizer


class Command(BaseCommand):
    """Summarize review text locally; never requires cloud inference."""

    help = "Summarize text with the deterministic backend (or an optional local LLM)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--text", type=str, default="", help="Inline text.")
        parser.add_argument("--file", type=str, default=None, help="Path to a text file.")
        parser.add_argument("--sentences", type=int, default=3, help="Max sentences.")
        parser.add_argument(
            "--backend",
            choices=["extractive", "transformers", "ollama"],
            default="extractive",
            help="Summarizer backend; optional backends fall back to extractive.",
        )

    def handle(self, *args, **options) -> None:
        text = options["text"]
        if options["file"]:
            text = Path(options["file"]).read_text(encoding="utf-8")
        if not text.strip():
            self.stderr.write(self.style.ERROR("No text provided."))
            return

        summarizer = build_summarizer(options["backend"])
        summary = summarizer.summarize(text, max_sentences=options["sentences"])
        self.stdout.write(
            self.style.SUCCESS(f"[backend={summarizer.backend}]\n{summary}")
        )
