"""
Central configuration for the ai_engine machine-learning package.

This module is intentionally free of Django imports so the same code can be
executed from management commands, standalone scripts, and tests.

Environment variables
---------------------
``AI_ARTIFACTS_DIR``
    Directory where trained models, indexes and manifests are written. It is
    kept **outside** version control (see ``.gitignore``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# ``apps/ai_engine/ml/config.py`` -> repository root is three parents up.
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACTS_DIR = REPO_ROOT / "ai_artifacts"
DEFAULT_SEED = 42


def get_artifacts_dir() -> Path:
    """Return the artifacts directory, creating it if necessary.

    Resolution order:

    1. ``AI_ARTIFACTS_DIR`` environment variable (used by tests/CI).
    2. The Django ``AI_ARTIFACTS_DIR`` setting when Django is configured.
    3. ``<repo>/ai_artifacts`` as the final default.
    """
    override = os.environ.get("AI_ARTIFACTS_DIR")
    if override:
        base = Path(override)
    else:
        base = None
        try:  # Use the Django setting when running inside the app.
            from django.conf import settings

            configured = getattr(settings, "AI_ARTIFACTS_DIR", None)
            if configured:
                base = Path(configured)
        except Exception:
            base = None
        if base is None:
            base = DEFAULT_ARTIFACTS_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base


@dataclass(frozen=True)
class RecommenderParams:
    """Hyper-parameters for the hybrid recommender.

    Attributes:
        n_components: Latent dimensions for truncated SVD matrix factorization.
        alpha: Weight of the collaborative signal in ``[0, 1]``; ``1 - alpha``
            weights the content signal.
        top_k: Default number of recommendations to return.
        min_item_interactions: Items with fewer interactions are ignored during
            training (kept low for tiny datasets).
    """

    n_components: int = 32
    alpha: float = 0.6
    top_k: int = 10
    min_item_interactions: int = 1


@dataclass(frozen=True)
class SplitParams:
    """Train/validation/test split configuration.

    Attributes:
        train_ratio: Fraction of interactions used for training.
        val_ratio: Fraction used for validation (model selection).
        test_ratio: Fraction used for the final held-out evaluation.
        seed: Random seed making the split reproducible.
    """

    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    seed: int = DEFAULT_SEED

    def validate(self) -> None:
        """Raise ``ValueError`` if the ratios do not sum to 1.0."""
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Split ratios must sum to 1.0 (got {total}).")


# Default evaluation cut-offs used by the training/evaluation scripts.
EVAL_K_VALUES = (5, 10)
