"""
Data-processing subpackage: generation, preprocessing, splitting and storage.

Everything here is deterministic given a seed, which is what makes the training
pipeline reproducible.
"""

from __future__ import annotations

__all__ = ["synthetic", "preprocessing", "dataset"]
