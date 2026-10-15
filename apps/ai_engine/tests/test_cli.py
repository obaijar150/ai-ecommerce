"""Tests for the standalone CLI entry points (no Django required)."""

from __future__ import annotations

import json

from apps.ai_engine.ml import cli


def test_generate_writes_dataset(tmp_path, capsys):
    """``generate`` writes a JSON dataset and prints a summary."""
    out = tmp_path / "dataset.json"
    exit_code = cli.main(
        ["generate", "--users", "10", "--items", "12", "--out", str(out)]
    )
    assert exit_code == 0
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["interactions"]
    assert payload["items"]


def test_train_prints_report(artifacts_dir, capsys):
    """``train`` runs end-to-end and prints a JSON report."""
    exit_code = cli.main(["train", "--users", "30", "--items", "40"])
    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["winner"] in {"hybrid", "popularity"}


def test_search_index_and_search_round_trip(artifacts_dir, capsys):
    """An index built by the CLI can be queried by the CLI."""
    cli.main(["search-index", "--users", "20", "--items", "30"])
    capsys.readouterr()
    exit_code = cli.main(["search", "--query", "premium electronics", "--k", "3"])
    assert exit_code == 0
    results = json.loads(capsys.readouterr().out)
    assert isinstance(results, list)


def test_summarize_command(capsys):
    """``summarize`` prints a non-empty summary."""
    exit_code = cli.main(
        [
            "summarize",
            "--text",
            "Good battery life. Great camera. Fast shipping. Excellent value.",
            "--sentences",
            "2",
        ]
    )
    assert exit_code == 0
    assert capsys.readouterr().out.strip()


def test_recommend_command(artifacts_dir, capsys):
    """``recommend`` works even without a trained artifact (fallback)."""
    exit_code = cli.main(["recommend", "--user", "u0", "--k", "3"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["algorithm"] == "popularity"
