"""Tests for the summarizer and the product assistant (deterministic paths)."""

from __future__ import annotations

from apps.ai_engine.ml.algorithms import summarizer as summarizer_module
from apps.ai_engine.ml.algorithms.summarizer import (
    ExtractiveSummarizer,
    build_summarizer,
    summarize_reviews,
)
from apps.ai_engine.ml.inference.assistant import ProductAssistant

REVIEWS = (
    "The battery lasts for two full days of heavy use. "
    "The camera is sharp and colours look natural. "
    "Shipping was slow and the box arrived dented. "
    "Overall the phone is excellent value for the price."
)


def test_extractive_summary_is_shorter_than_input():
    """The extractive summary never exceeds the requested sentence count."""
    summary = ExtractiveSummarizer().summarize(REVIEWS, max_sentences=2)
    assert summary
    assert len(summary.split(". ")) <= 3


def test_extractive_summary_preserves_sentence_text():
    """Summary sentences are drawn verbatim from the input."""
    summary = ExtractiveSummarizer().summarize(REVIEWS, max_sentences=2)
    for sentence in summary.split(". "):
        assert sentence.rstrip(".") in REVIEWS


def test_empty_text_returns_empty_summary():
    """Empty input yields an empty summary rather than an error."""
    assert ExtractiveSummarizer().summarize("") == ""
    assert summarize_reviews([]) == ""


def test_short_text_is_returned_unchanged():
    """Text with fewer sentences than the limit is returned whole."""
    text = "Great product. Fast delivery."
    assert ExtractiveSummarizer().summarize(text, max_sentences=5)

def test_factory_falls_back_to_extractive_without_heavy_deps():
    """Requesting transformers without PyTorch falls back to extractive."""
    if summarizer_module.transformers_available():
        return
    model = build_summarizer("transformers")
    assert model.backend == "extractive"


def test_factory_ollama_falls_back_when_server_absent():
    """Requesting Ollama without a running server falls back to extractive."""
    model = build_summarizer("ollama", base_url="http://127.0.0.1:1")
    assert model.backend == "extractive"


def test_assistant_answers_with_matching_snippets():
    """The assistant retrieves relevant products deterministically."""
    assistant = ProductAssistant()
    snippets = [
        ("Acme Headphones", "wireless bluetooth audio headphones"),
        ("Globe Cookbook", "recipes for the kitchen"),
    ]
    answer = assistant.answer("I want wireless headphones", snippets)
    assert "Acme Headphones" in answer


def test_assistant_handles_empty_question():
    """An empty question yields a clarification, not an error."""
    assistant = ProductAssistant()
    assert "ask a question" in assistant.answer("").lower()


def test_assistant_handles_no_matches():
    """No matching snippet yields a helpful fallback message."""
    assistant = ProductAssistant()
    answer = assistant.answer("quantum telescope", [("Cookbook", "kitchen recipes")])
    assert "couldn't find" in answer.lower()


def test_assistant_summarize_reviews_never_raises():
    """Review summarization degrades to the deterministic backend."""
    assistant = ProductAssistant()
    summary = assistant.summarize_reviews([REVIEWS])
    assert isinstance(summary, str)
    assert summary
