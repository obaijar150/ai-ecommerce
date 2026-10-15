"""
Text normalization helpers used by search and the chatbot.

All functions are pure, dependency-free and safe to call on ``None``/empty input.
"""

from __future__ import annotations

import re
import unicodedata


def normalize(text: str | None) -> str:
    """Return a canonical, lower-cased, whitespace-collapsed form of ``text``.

    Punctuation is replaced with spaces so downstream tokenizers never choke on
    attached symbols such as ``headphone's`` or ``laptop-case``.
    """
    if not text:
        return ""
    value = unicodedata.normalize("NFKC", str(text))
    value = value.lower()
    value = re.sub(r"[^\w\s-]", " ", value)
    value = re.sub(r"[\s_-]+", " ", value)
    return value.strip()


def tokens(text: str | None) -> list[str]:
    """Return the alphanumeric tokens of ``text`` in normalized form."""
    return [token for token in normalize(text).split() if token]


def slugify_phrase(text: str | None) -> str:
    """Return a hyphenated, filesystem/URL safe version of ``text``."""
    return re.sub(r"\s+", "-", normalize(text)).strip("-")
