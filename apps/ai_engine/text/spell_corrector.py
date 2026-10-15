"""
Spell correction for search queries.

Combines two free, open-source libraries:

* ``symspellpy`` (MIT) for fast, dictionary-based correction with edit distance.
* ``rapidfuzz`` (MIT) as a fallback for vocabulary-less or out-of-dictionary
  terms, using token-level fuzzy similarity.

The corrector is vocabulary-driven: pass in the words you care about (product
names/tokens). When no vocabulary is supplied it is a passthrough, so the
module never breaks a pipeline on missing data.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence

try:  # Optional dependency; pure-Python fallback paths still work.
    from symspellpy import SymSpell

    _SYMSPELL_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only if symspellpy missing
    SymSpell = None  # type: ignore[assignment]
    _SYMSPELL_AVAILABLE = False

try:  # Optional dependency; passthrough if unavailable.
    from rapidfuzz import process as _rf_process
    from rapidfuzz import fuzz as _rf_fuzz

    _RAPIDFUZZ_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only if rapidfuzz missing
    _rf_process = None  # type: ignore[assignment]
    _rf_fuzz = None  # type: ignore[assignment]
    _RAPIDFUZZ_AVAILABLE = False


class SpellCorrector:
    """Correct tokens against a supplied vocabulary.

    Attributes:
        vocabulary: Deduplicated list of accepted tokens.
        max_edit_distance: Maximum edit distance for SymSpell lookups.
    """

    def __init__(
        self,
        vocabulary: Iterable[str] | None = None,
        max_edit_distance: int = 2,
    ) -> None:
        self.vocabulary: list[str] = list(dict.fromkeys(vocabulary or []))
        self.max_edit_distance = max_edit_distance
        self._sym_spell = None
        if _SYMSPELL_AVAILABLE and self.vocabulary:
            self._sym_spell = SymSpell(max_dictionary_edit_distance=max_edit_distance)
            counts = Counter(self.vocabulary)
            for word, count in counts.items():
                self._sym_spell.create_dictionary_entry(str(word), int(count))

    def available(self) -> bool:
        """Return whether any correction backend is ready."""
        return bool(self.vocabulary) and (_SYMSPELL_AVAILABLE or _RAPIDFUZZ_AVAILABLE)

    def correct_token(self, token: str) -> str:
        """Correct a single token against the vocabulary."""
        if not token or token.isdigit():
            return token
        if not self.vocabulary:
            return token

        # Prefer SymSpell for speed and ranking.
        if self._sym_spell is not None:
            suggestions = self._sym_spell.lookup(
                token,
                verbosity=0,
                max_edit_distance=self.max_edit_distance,
            )
            if suggestions:
                # SymSpell ranks by edit distance then frequency.
                return str(suggestions[0].term)

        # RapidFuzz fallback: pick the closest vocabulary entry.
        if _RAPIDFUZZ_AVAILABLE:
            match = _rf_process.extractOne(
                token, self.vocabulary, scorer=_rf_fuzz.ratio
            )
            if match and match[1] >= 80 and match[0].lower() != token.lower():
                return str(match[0])

        return token

    def correct_text(self, text: str) -> str:
        """Correct every whitespace-separated token in ``text``."""
        from .normalizer import normalize, tokens as normalize_tokens

        normalized = normalize(text)
        if not normalized:
            return ""
        corrected = [self.correct_token(token) for token in normalized.split()]
        return " ".join(corrected)

    def closest(self, query: str, candidates: Sequence[str], limit: int = 5) -> list[tuple[str, int]]:
        """Return the closest ``candidates`` to ``query`` via rapidfuzz."""
        if not _RAPIDFUZZ_AVAILABLE or not candidates:
            return []
        results = _rf_process.extract(query, candidates, scorer=_rf_fuzz.WRatio, limit=limit)
        return [(str(item[0]), int(item[1])) for item in results]


def build_vocabulary_from_texts(texts: Iterable[str]) -> list[str]:
    """Build a de-duplicated vocabulary (tokens) from ``texts``."""
    from .normalizer import tokens

    collected: set[str] = set()
    for text in texts:
        collected.update(tokens(text))
    return sorted(collected)


def default_corrector() -> SpellCorrector:
    """Return a corrector built from the live catalog when Django is available.

    Returns a passthrough corrector if the ORM is unavailable (e.g. tests that
    do not seed a catalog, or pure library usage).
    """
    try:
        from django.apps import apps

        if not apps.ready:
            return SpellCorrector()
        from django.db import connection

        connection.ensure_connection()
    except Exception:
        return SpellCorrector()

    try:
        # Late import to keep this module Django-agnostic at import time.
        from apps.catalog.models import Product

        texts = list(Product.objects.filter(is_active=True).values_list("name", "description", flat=False))
        collected: list[str] = []
        for name, description in texts:
            collected.append(name or "")
            collected.append(description or "")
        return SpellCorrector(build_vocabulary_from_texts(collected))
    except Exception:
        return SpellCorrector()
