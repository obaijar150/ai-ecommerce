"""Tests for the text normalizer and spell corrector."""

from __future__ import annotations

import pytest

from apps.ai_engine.text.normalizer import normalize, tokens, slugify_phrase
from apps.ai_engine.text.spell_corrector import SpellCorrector, build_vocabulary_from_texts


def test_normalize_lowercases_and_collapses_whitespace():
    assert normalize("  Hello   WORLD  ") == "hello world"


def test_normalize_replaces_punctuation_with_spaces():
    assert normalize("headphone's, case-style") == "headphone s case style"


def test_normalize_handles_none():
    assert normalize(None) == ""
    assert tokens(None) == []


def test_tokens_returns_list():
    assert tokens("Aurora X1 Smartphone") == ["aurora", "x1", "smartphone"]


def test_slugify_phrase():
    assert slugify_phrase("Wireless Bluetooth Headphones") == "wireless-bluetooth-headphones"


def test_spell_corrector_passthrough_without_vocabulary():
    corrector = SpellCorrector()
    assert corrector.correct_text("hello world") == "hello world"
    assert corrector.available() is False


def test_spell_corrector_fixes_typos_with_vocabulary():
    vocab = build_vocabulary_from_texts(["Wireless Bluetooth Headphones"])
    corrector = SpellCorrector(vocab)
    assert "headphones" in corrector.correct_text("hedphones")


def test_spell_corrector_preserves_numbers():
    corrector = SpellCorrector(["item1", "item2"])
    assert corrector.correct_token("123") == "123"


def test_closest_returns_ranked_matches():
    corrector = SpellCorrector(["alpha", "beta", "gamma"])
    results = corrector.closest("alph", ["alpha", "beta", "gamma"], limit=2)
    assert results
    assert results[0][0] == "alpha"


@pytest.mark.django_db
def test_default_corrector_uses_catalog_when_available(db):
    from apps.catalog.tests.factories import ProductFactory

    ProductFactory(name="Vertex Studio Headphones")
    from apps.ai_engine.text.spell_corrector import default_corrector

    corrector = default_corrector()
    assert corrector.available() is True
    assert "headphones" in corrector.correct_text("hedphones")
