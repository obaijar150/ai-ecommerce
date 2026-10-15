"""
Product assistant and review-summary inference.

Combines two deterministic capabilities with optional LLM backing:

* **Review summarization** delegates to the summarizer backends. If an optional
  LLM (Ollama / transformers) is unavailable, the extractive summarizer answers.
* **Product Q&A** is a lightweight, deterministic retrieval over supplied
  catalog snippets; the optional Ollama LLM can rewrite the answer when present
  but is never required.

Nothing here needs a network connection or an API key.
"""

from __future__ import annotations

from typing import Sequence

from ..algorithms.summarizer import (
    ExtractiveSummarizer,
    OllamaSummarizer,
    build_summarizer,
    summarize_reviews,
)
from ..data.preprocessing import content_tokens


class ProductAssistant:
    """Deterministic product assistant with optional local-LLM augmentation.

    Attributes:
        summarizer: Active summarizer backend.
        llm: Optional Ollama backend used for fluent answers, else ``None``.
        backend: Name of the summarizer backend in use.
    """

    def __init__(
        self,
        summary_backend: str = "extractive",
        ollama_model: str = "qwen2.5:0.5b",
        base_url: str = "http://localhost:11434",
        enable_llm: bool = False,
    ) -> None:
        self.summarizer = build_summarizer(
            "ollama" if enable_llm else summary_backend,
            model=ollama_model,
            base_url=base_url,
        )
        self.llm = None
        if enable_llm and isinstance(self.summarizer, OllamaSummarizer):
            self.llm = self.summarizer
        elif enable_llm:
            candidate = OllamaSummarizer(model=ollama_model, base_url=base_url)
            if candidate.is_available():
                self.llm = candidate
        self.backend = getattr(self.summarizer, "backend", "extractive")

    def summarize_reviews(self, reviews: Sequence[str], max_sentences: int = 3) -> str:
        """Summarize review bodies with graceful fallback.

        Optional backend failures never propagate: the extractive summarizer is
        used instead and the caller always receives text.
        """
        try:
            return self.summarizer.summarize(
                " ".join(review.strip() for review in reviews if review and review.strip()),
                max_sentences=max_sentences,
            )
        except Exception:
            return ExtractiveSummarizer().summarize(
                " ".join(review.strip() for review in reviews if review and review.strip()),
                max_sentences=max_sentences,
            )

    def answer(self, question: str, catalog_snippets: Sequence[tuple[str, str]] | None = None) -> str:
        """Answer a product question deterministically.

        Args:
            question: The user's question.
            catalog_snippets: ``(name, text)`` pairs to retrieve from.

        Returns:
            A grounded answer composed from the best-matching snippets. When no
            snippet matches, a polite clarification is returned.
        """
        if not question or not question.strip():
            return "Please ask a question about a product."

        snippets = catalog_snippets or []
        query_tokens = set(content_tokens(question))
        scored: list[tuple[float, str]] = []
        for name, text in snippets:
            combined = f"{name} {text}"
            tokens = set(content_tokens(combined))
            if not tokens:
                continue
            overlap = len(query_tokens & tokens)
            score = overlap / (len(query_tokens) or 1)
            if overlap:
                scored.append((score, name))

        if not scored:
            return (
                "I couldn't find a matching product. Try rephrasing or browse the "
                "catalog categories."
            )

        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        names = [name for _, name in scored[:3]]
        joined = ", ".join(names)
        base = f"Based on the catalog, these products look relevant: {joined}."

        if self.llm is not None:
            try:
                prompt = f"{base} Answer the shopper's question: {question}"
                return self.llm.summarize(prompt, max_sentences=2) or base
            except Exception:
                return base
        return base


def summarize(reviews: Sequence[str], max_sentences: int = 3, backend: str = "extractive") -> str:
    """Module-level convenience wrapper around :func:`summarize_reviews`."""
    return summarize_reviews(reviews, max_sentences=max_sentences, backend=backend)
