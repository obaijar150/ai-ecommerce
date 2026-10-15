"""
Machine-learning subpackage for the ai_engine app.

The package is split into clearly separated concerns:

* ``data``        — dataset generation and processing (splits, matrices).
* ``algorithms``  — baseline and learned model implementations.
* ``training``    — reproducible training entry points.
* ``evaluation``  — metrics and model comparison.
* ``inference``   — loading trained artifacts and serving predictions.

Nothing here imports Django at module import time, so the code can run as a
plain library. Django-aware glue lives in ``apps/ai_engine/services`` and the
``ai_*`` management commands.
"""

from __future__ import annotations

__all__ = [
    "config",
    "licenses",
    "artifacts",
]
