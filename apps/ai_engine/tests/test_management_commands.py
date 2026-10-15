"""Tests for the ``ai_*`` management commands."""

from __future__ import annotations

import json

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_generate_dataset_command(artifacts_dir, capsys):
    """``ai_generate_dataset`` writes a dataset file."""
    call_command("ai_generate_dataset", "--users", "10", "--items", "12")
    out = capsys.readouterr().out
    assert "interactions" in out
    assert (artifacts_dir / "datasets" / "synthetic.json").exists()


@pytest.mark.django_db
def test_train_recommender_command(artifacts_dir, capsys):
    """``ai_train_recommender`` trains on synthetic data and reports a winner."""
    call_command("ai_train_recommender", "--users", "40", "--items", "50")
    report = json.loads(capsys.readouterr().out)
    assert report["winner"] in {"hybrid", "popularity"}
    assert report["artifact"]["name"] == "recommender"


@pytest.mark.django_db
def test_build_embedding_index_command(artifacts_dir, capsys):
    """``ai_build_embedding_index`` builds a TF-IDF index by default."""
    call_command("ai_build_embedding_index", "--items", "30")
    report = json.loads(capsys.readouterr().out)
    assert report["actual_backend"] == "tfidf"
    assert report["num_items"] > 0


@pytest.mark.django_db
def test_evaluate_recommender_command(artifacts_dir, capsys):
    """``ai_evaluate_recommender`` prints baseline and artifact metrics."""
    call_command("ai_train_recommender", "--users", "40", "--items", "50")
    capsys.readouterr()
    call_command("ai_evaluate_recommender", "--users", "40", "--items", "50")
    report = json.loads(capsys.readouterr().out)
    assert "baseline" in report
    assert "artifact" in report


@pytest.mark.django_db
def test_summarize_command(artifacts_dir, capsys):
    """``ai_summarize`` prints a summary with its backend."""
    call_command(
        "ai_summarize",
        "--text",
        "Battery is great. Camera is sharp. Shipping was slow. Good value.",
    )
    out = capsys.readouterr().out
    assert "backend=" in out
