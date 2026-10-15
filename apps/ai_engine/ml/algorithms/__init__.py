"""
Algorithm implementations: baselines and learned models.

Each algorithm exposes a small, uniform interface so the training and
evaluation code can treat them interchangeably::

    model.fit(train_interactions, item_features)
    model.recommend(user_id, k, exclude_seen) -> list[item_id]
    model.score(user_id, item_ids) -> list[float]
"""

from __future__ import annotations

__all__ = ["popularity", "hybrid_recommender", "text_embedding", "summarizer"]
