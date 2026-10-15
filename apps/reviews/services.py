"""
Reviews services: AI-powered review summarization.

Uses NLTK for extractive summarization (free, open-source, no API calls).
"""

import logging
from typing import Optional

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

from apps.catalog.models import Product

from .models import Review, ReviewSummary

logger = logging.getLogger(__name__)

# Ensure NLTK data is available (download once)
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)


class ReviewSummarizationService:
    """Service for generating AI summaries from product reviews."""

    MAX_SENTENCES = 5

    @staticmethod
    def generate_summary(product: Product) -> Optional[ReviewSummary]:
        """Generate an extractive summary of all reviews for a product."""
        reviews = Review.objects.filter(product=product)
        if not reviews.exists():
            return None

        # Combine all review texts
        all_text = " ".join([f"{r.title}. {r.body}" for r in reviews])

        # Extractive summarization using sentence scoring
        summary_text = ReviewSummarizationService._extractive_summary(all_text)

        # Calculate average sentiment score
        avg_rating = reviews.aggregate(avg=models.Avg("rating"))["avg"] or 3
        sentiment_score = round((avg_rating - 3) / 2, 2)  # Normalize to -1..1

        # Save or update summary
        summary_obj, created = ReviewSummary.objects.update_or_create(
            product=product,
            defaults={
                "summary": summary_text,
                "sentiment_score": sentiment_score,
                "model_version": "nltk-extractive-v1",
            },
        )

        action = "Created" if created else "Updated"
        logger.info(f"{action} review summary for {product.name}")

        return summary_obj

    @staticmethod
    def _extractive_summary(text: str) -> str:
        """Generate extractive summary by scoring sentences."""
        sentences = sent_tokenize(text)

        if len(sentences) <= ReviewSummarizationService.MAX_SENTENCES:
            return " ".join(sentences)

        # Score sentences by word frequency (excluding stopwords)
        stop_words = set(stopwords.words("english"))
        word_freq = {}

        for word in word_tokenize(text.lower()):
            if word.isalnum() and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Score each sentence
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            words = word_tokenize(sentence.lower())
            score = sum(word_freq.get(w, 0) for w in words if w.isalnum())
            # Normalize by sentence length to avoid bias toward long sentences
            sentence_scores[i] = score / max(len(words), 1)

        # Select top N sentences, preserving original order
        top_indices = sorted(
            sorted(sentence_scores, key=sentence_scores.get, reverse=True)[
                : ReviewSummarizationService.MAX_SENTENCES
            ]
        )

        summary_sentences = [sentences[i] for i in top_indices]
        return " ".join(summary_sentences)
