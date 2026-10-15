"""Tests for the license registry and its permissive-default guarantee."""

from __future__ import annotations

import pytest

from apps.ai_engine.ml import licenses


def test_all_components_have_license_metadata():
    """Every registered component carries a non-empty license and source."""
    for key, info in licenses.all_components().items():
        assert info.license, f"{key} is missing a license"
        assert info.source, f"{key} is missing a source"
        assert info.kind is not None


def test_core_components_are_permissive():
    """The baseline, trained model and synthetic dataset are all permissive."""
    registry = licenses.all_components()
    for key in ("tfidf_baseline", "popularity_baseline", "hybrid_recommender", "synthetic"):
        assert registry[key].permissive is True


def test_non_permissive_components_are_flagged():
    """Non-permissive models/datasets are explicitly marked."""
    flagged = {info.name for info in licenses.non_permissive_components()}
    assert any("Llama" in name for name in flagged)
    assert any("MovieLens" in name for name in flagged)


def test_assert_no_non_permissive_defaults_allows_permissive():
    """Enabling only permissive components does not raise."""
    licenses.assert_no_non_permissive_defaults(["hybrid_recommender", "synthetic"])


def test_assert_no_non_permissive_defaults_rejects_non_permissive():
    """Enabling a non-permissive component raises a clear error."""
    with pytest.raises(ValueError, match="Non-permissive"):
        licenses.assert_no_non_permissive_defaults(["llama3.2-1b"])


def test_unknown_components_are_ignored():
    """Unregistered identifiers are ignored rather than raising."""
    licenses.assert_no_non_permissive_defaults(["some-future-model"])
