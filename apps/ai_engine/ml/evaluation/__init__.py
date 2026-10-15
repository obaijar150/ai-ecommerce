"""
Evaluation metrics and model-comparison helpers.

All metrics operate on a per-user ranked list against a set of held-out
relevant items, which is the standard offline protocol for implicit-feedback
recommendation.
"""

from __future__ import annotations

__all__ = ["metrics", "evaluate_recommender"]
