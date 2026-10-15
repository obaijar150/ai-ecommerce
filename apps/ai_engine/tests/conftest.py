"""
Shared pytest fixtures for ai_engine ML tests.

Every test that persists artifacts gets an isolated temporary artifacts
directory via the ``AI_ARTIFACTS_DIR`` environment variable, so the developer's
real ``ai_artifacts/`` folder is never touched.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def artifacts_dir(tmp_path, monkeypatch):
    """Point the artifact registry at an isolated temporary directory."""
    target = tmp_path / "ai_artifacts"
    monkeypatch.setenv("AI_ARTIFACTS_DIR", str(target))
    target.mkdir(parents=True, exist_ok=True)
    return target


@pytest.fixture()
def synthetic_dataset():
    """A small deterministic synthetic dataset for fast tests."""
    from apps.ai_engine.ml.data.synthetic import generate_dataset

    return generate_dataset(
        n_users=30, n_items=40, interactions_per_user=8, seed=7
    )
