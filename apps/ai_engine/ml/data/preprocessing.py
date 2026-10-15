"""
Text preprocessing shared by embeddings and the summarizer.

Kept dependency-free (no NLTK corpus downloads) so it works offline. The
stop-word list is intentionally small and is only used by the *baseline*
extractive summarizer; embeddings rely on scikit-learn's own analyzer.
"""

from __future__ import annotations

import re
from typing import Iterable

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# A compact English stop-word list. Deliberately not downloaded from NLTK so
# the pipeline never needs network access.
STOP_WORDS = frozenset(
    """
    a an and are as at be but by for if in into is it no not of on or such
    that the their then there these they this to was will with we you your
    our from has have had do does did done can could would should may might
    """.split()
)

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def normalize_text(text: str) -> str:
    """Lower-case and collapse whitespace."""
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def tokenize(text: str) -> list[str]:
    """Return lower-cased alphanumeric tokens."""
    return _TOKEN_RE.findall((text or "").lower())


def content_tokens(text: str) -> list[str]:
    """Return tokens with stop words removed."""
    return [token for token in tokenize(text) if token not in STOP_WORDS]


def split_sentences(text: str) -> list[str]:
    """Split text into trimmed, non-empty sentences."""
    parts = _SENTENCE_RE.split((text or "").strip())
    return [part.strip() for part in parts if part.strip()]


def truncate(text: str, max_chars: int) -> str:
    """Truncate ``text`` to ``max_chars`` characters on a word boundary."""
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip() + "…"


def join_tokens(tokens: Iterable[str]) -> str:
    """Join tokens with single spaces."""
    return " ".join(tokens)
