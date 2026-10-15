"""
Inference subpackage: load trained artifacts and serve predictions.

All loaders degrade gracefully — if no artifact exists they fall back to a
deterministic behaviour (popularity ranking, substring/ TF-IDF search, or the
extractive summarizer) so the web app never breaks because a model has not been
trained yet.
"""

from __future__ import annotations

__all__ = ["recommender", "semantic_search", "assistant"]
