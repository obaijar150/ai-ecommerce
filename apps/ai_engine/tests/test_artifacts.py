"""Tests for the artifact registry and model versioning."""

from __future__ import annotations

import pytest

from apps.ai_engine.ml import artifacts


class _DummyModel:
    """Minimal picklable object used to exercise the registry."""

    def __init__(self, value: int = 1) -> None:
        self.value = value


def test_save_and_load_round_trip(artifacts_dir):
    """A saved artifact loads back with its metadata."""
    saved = artifacts.save_artifact(
        "dummy", _DummyModel(7), {"kind": "test"}, artifacts_dir=artifacts_dir
    )
    model, metadata = artifacts.load_artifact("dummy", artifacts_dir=artifacts_dir)
    assert model.value == 7
    assert metadata["kind"] == "test"
    assert metadata["version"] == saved.version


def test_metadata_records_reproducibility_fields(artifacts_dir):
    """Manifests capture seed/params, libraries and git commit."""
    artifacts.save_artifact(
        "dummy",
        _DummyModel(),
        {"params": {"seed": 42}, "kind": "test"},
        artifacts_dir=artifacts_dir,
    )
    _model, metadata = artifacts.load_artifact("dummy", artifacts_dir=artifacts_dir)
    assert metadata["params"]["seed"] == 42
    assert "libraries" in metadata
    assert "git_commit" in metadata
    assert "created_at" in metadata


def test_latest_pointer_points_to_newest(artifacts_dir):
    """Saving twice makes the second version latest."""
    first = artifacts.save_artifact(
        "dummy", _DummyModel(1), {}, version="v1", artifacts_dir=artifacts_dir
    )
    second = artifacts.save_artifact(
        "dummy", _DummyModel(2), {}, version="v2", artifacts_dir=artifacts_dir
    )
    assert artifacts.latest_version("dummy", artifacts_dir) == second.version
    assert first.version == "v1"
    assert artifacts.list_versions("dummy", artifacts_dir) == ["v1", "v2"]


def test_load_specific_version(artifacts_dir):
    """A specific historic version can be loaded."""
    artifacts.save_artifact(
        "dummy", _DummyModel(1), {}, version="v1", artifacts_dir=artifacts_dir
    )
    artifacts.save_artifact(
        "dummy", _DummyModel(2), {}, version="v2", artifacts_dir=artifacts_dir
    )
    model, metadata = artifacts.load_artifact("dummy", "v1", artifacts_dir=artifacts_dir)
    assert model.value == 1
    assert metadata["version"] == "v1"


def test_missing_artifact_raises(artifacts_dir):
    """Loading an unknown artifact raises ``FileNotFoundError``."""
    with pytest.raises(FileNotFoundError):
        artifacts.load_artifact("nope", artifacts_dir=artifacts_dir)


def test_list_versions_empty_when_absent(artifacts_dir):
    """An unknown artifact has no versions."""
    assert artifacts.list_versions("nope", artifacts_dir=artifacts_dir) == []
    assert artifacts.latest_version("nope", artifacts_dir=artifacts_dir) is None


def test_fingerprint_is_stable_and_sensitive():
    """Fingerprints are stable for equal payloads and differ otherwise."""
    assert artifacts.fingerprint({"a": 1}) == artifacts.fingerprint({"a": 1})
    assert artifacts.fingerprint({"a": 1}) != artifacts.fingerprint({"a": 2})
