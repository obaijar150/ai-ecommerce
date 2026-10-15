"""
Reproducible training entry points.

These functions are pure-Python and Django-agnostic; the ``ai_*`` management
commands and the standalone scripts call them. Every run records the seed,
hyper-parameters, dataset fingerprint, library versions and evaluation report in
the artifact manifest so results can be reproduced and audited.
"""

from __future__ import annotations

__all__ = ["train_recommender", "build_embedding_index"]
