"""
Summarization backends for review summaries and the product assistant.

* ``extractive`` (default) — a deterministic frequency-based extractive
  summarizer written here. It needs no model download and always works.
* ``transformers`` (optional) — a small pretrained seq2seq model such as
  ``google/flan-t5-small`` (Apache-2.0), used **as-is**. Only attempted when
  ``transformers`` and PyTorch are importable.
* ``ollama`` (optional) — a locally served open-weight LLM via the Ollama
  runtime (e.g. ``qwen2.5:0.5b``). Reached over HTTP at ``localhost``; no cloud
  inference and no API keys.

The deterministic backend is the contract: if the optional backends are
unavailable the engine still produces a summary.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from ..data.preprocessing import content_tokens, split_sentences, truncate


def transformers_available() -> bool:
    """Return whether ``transformers`` and PyTorch can be imported."""
    try:  # pragma: no cover - optional dependency
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except Exception:
        return False
    return True


class ExtractiveSummarizer:
    """Deterministic frequency-based extractive summarizer.

    Scores each sentence by the summed frequency of its content tokens and
    returns the highest-scoring sentences in their original order.
    """

    backend = "extractive"

    def summarize(self, text: str, max_sentences: int = 3) -> str:
        """Return a short extractive summary of ``text``.

        Args:
            text: Input document (e.g. concatenated reviews).
            max_sentences: Maximum sentences in the summary.

        Returns:
            A trimmed summary string, or ``""`` for empty input.
        """
        sentences = split_sentences(text)
        if not sentences:
            return ""
        if len(sentences) <= max_sentences:
            return " ".join(sentences)

        frequencies = Counter(content_tokens(text))
        if not frequencies:
            return " ".join(sentences[:max_sentences])

        scored: list[tuple[int, float]] = []
        for index, sentence in enumerate(sentences):
            tokens = content_tokens(sentence)
            if not tokens:
                score = 0.0
            else:
                score = sum(frequencies[token] for token in tokens) / len(tokens)
            scored.append((index, score))

        best = sorted(scored, key=lambda pair: (-pair[1], pair[0]))[:max_sentences]
        ordered = sorted(index for index, _ in best)
        return " ".join(sentences[index] for index in ordered)


class TransformerSummarizer:
    """Optional pretrained seq2seq summarizer (used as-is, not trained here)."""

    backend = "transformers"

    def __init__(self, model_name: str = "google/flan-t5-small", max_length: int = 150) -> None:
        self.model_name = model_name
        self.max_length = max_length
        self._pipeline: Any = None

    def _load(self) -> Any:
        """Lazily build the Hugging Face summarization pipeline."""
        if self._pipeline is None:
            from transformers import pipeline  # noqa: WPS433

            self._pipeline = pipeline("text2text-generation", model=self.model_name)
        return self._pipeline

    def summarize(self, text: str, max_sentences: int = 3) -> str:
        """Summarize with the pretrained model, truncating long inputs."""
        if not text.strip():
            return ""
        pipe = self._load()
        prompt = f"Summarize the following product reviews: {truncate(text, 2000)}"
        result = pipe(prompt, max_length=self.max_length, do_sample=False)
        if isinstance(result, list) and result:
            return str(result[0].get("generated_text", "")).strip()
        return ""  # pragma: no cover - defensive


class OllamaSummarizer:
    """Optional local LLM summarizer served by Ollama over HTTP."""

    backend = "ollama"

    def __init__(
        self,
        model: str = "qwen2.5:0.5b",
        base_url: str = "http://localhost:11434",
        timeout: float = 30.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        """Return whether the local Ollama server responds."""
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=2) as response:
                return response.status == 200
        except Exception:
            return False

    def summarize(self, text: str, max_sentences: int = 3) -> str:
        """Summarize via the local Ollama server.

        Raises:
            RuntimeError: If the server is unreachable or returns an error.
        """
        import json
        import urllib.request

        if not text.strip():
            return ""
        prompt = (
            "Summarize these product reviews in at most "
            f"{max_sentences} sentences:\n\n{truncate(text, 4000)}"
        )
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                return str(body.get("response", "")).strip()
        except Exception as exc:  # pragma: no cover - needs a live server
            raise RuntimeError(f"Ollama request failed: {exc}") from exc


def build_summarizer(backend: str = "extractive", **kwargs: Any):
    """Factory returning a summarizer for ``backend`` with safe fallback.

    Args:
        backend: ``"extractive"``, ``"transformers"`` or ``"ollama"``.
        **kwargs: Forwarded to the selected backend.

    Returns:
        A summarizer exposing ``summarize(text, max_sentences)``.
    """
    if backend == "transformers" and transformers_available():
        return TransformerSummarizer(
            model_name=kwargs.get("model_name", "google/flan-t5-small"),
            max_length=kwargs.get("max_length", 150),
        )
    if backend == "ollama":
        candidate = OllamaSummarizer(
            model=kwargs.get("model", "qwen2.5:0.5b"),
            base_url=kwargs.get("base_url", "http://localhost:11434"),
        )
        if candidate.is_available():
            return candidate
    return ExtractiveSummarizer()


def summarize_reviews(reviews: Sequence[str], max_sentences: int = 3, backend: str = "extractive") -> str:
    """Convenience helper summarizing a list of review bodies.

    Args:
        reviews: Review text fragments.
        max_sentences: Maximum sentences in the output.
        backend: Summarizer backend to request.

    Returns:
        A summary string (deterministic fallback guarantees non-error).
    """
    joined = " ".join(review.strip() for review in reviews if review and review.strip())
    return build_summarizer(backend).summarize(joined, max_sentences=max_sentences)
