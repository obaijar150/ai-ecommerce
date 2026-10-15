"""
AI Shopping Assistant chatbot service.

The assistant is grounded in the live catalog, search index, recommendation
engine, orders and reviews, so answers reflect the real store instead of
canned templates. Heavy ML is optional: intent classification, embeddings,
recommendations and summarization all degrade to deterministic keyword/TF-IDF
behaviour when their optional dependencies are missing.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from typing import Optional, Tuple

from django.conf import settings

from apps.ai_engine.models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)

# Stop words stripped when extracting a product query from a full sentence.
_QUERY_STOP_WORDS = {
    "a", "an", "the", "i", "me", "my", "want", "need", "looking", "for",
    "find", "show", "search", "buy", "get", "give", "tell", "about", "details",
    "info", "information", "price", "of", "please", "some", "good", "best",
    "any", "can", "you", "recommend", "suggest", "something", "product", "item",
    "review", "reviews", "summarize", "summary", "rating", "ratings",
    "under", "over", "less", "more", "around",
}


class ChatbotService:
    """Service for the AI shopping assistant."""

    # Keyword intent patterns. Ordered so more specific intents win ties.
    INTENT_PATTERNS = {
        "greeting": [
            r"^\s*(hi|hello|hey|yo|hiya|good morning|good afternoon|good evening)\b",
            r"^\s*(thanks|thank you|thx)\b",
        ],
        "help": [
            r"\b(help|how (do|can|to)|what can you|capabilities|support|assist)\b",
        ],
        "order_status": [
            r"\b(order|orders|track|tracking|where is|shipping|delivery|arrive|arrived)\b",
            r"#?[0-9a-f]{8}-[0-9a-f]{4}-",
            r"order\s+(number|no\.?|#)",
        ],
        "review_summary": [
            r"\b(review|reviews|summar(y|ize|ise)|rating|ratings)\b",
        ],
        "recommendation": [
            r"\b(recommend|suggest|best|top|popular|trending|what (should|to) (buy|choose|get))\b",
            r"\b(for me|gift|gifts)\b",
        ],
        "product_search": [
            r"\b(find|search|show|looking|need|want|buy|shop|price|cost|available|in stock)\b",
            r"\b(product|item|thing|gadget|device|accessory)\b",
        ],
    }

    # Friendly one-line capabilities summary.
    CAPABILITIES = (
        "I can help you with:\n"
        "- Finding products (\"find wireless headphones\")\n"
        "- Prices and product details (\"price of the Aurora phone\")\n"
        "- Recommendations (\"recommend something for travel\")\n"
        "- Order status (\"where is my order #...\")\n"
        "- Review summaries (\"summarize reviews for ...\")\n"
        "\nJust ask me anything in plain English."
    )

    # ------------------------------------------------------------------ #
    # Sessions and persistence
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_or_create_session(user=None, session_key: Optional[str] = None):
        """Get an active chat session or create a new one."""
        session = None
        if user and user.is_authenticated:
            session = ChatSession.objects.filter(user=user, ended_at__isnull=True).first()
        elif session_key:
            session = ChatSession.objects.filter(
                session_key=session_key, ended_at__isnull=True
            ).first()

        if not session:
            session = ChatSession.objects.create(
                user=user if user and user.is_authenticated else None,
                session_key=session_key if not (user and user.is_authenticated) else None,
            )
        return session

    @staticmethod
    def save_message(
        session: ChatSession,
        sender: str,
        message: str,
        intent: str = "",
        confidence: Optional[float] = None,
    ) -> ChatMessage:
        """Persist a chat message."""
        return ChatMessage.objects.create(
            session=session,
            sender=sender,
            message=message,
            intent=intent,
            confidence=confidence,
        )

    # ------------------------------------------------------------------ #
    # Intent classification
    # ------------------------------------------------------------------ #
    @staticmethod
    def classify_intent(message: str) -> Tuple[str, float]:
        """Classify a user message into one of the supported intents."""
        from apps.ai_engine.text.normalizer import normalize

        message_lower = normalize(message)
        if not message_lower:
            return "fallback", 1.0

        # Try the trained scikit-learn classifier first when present.
        intent, confidence = ChatbotService._ml_classify(message_lower)
        if intent and confidence and confidence > 0.6:
            return intent, confidence

        return ChatbotService._keyword_classify(message_lower)

    @staticmethod
    def _ml_classify(message: str) -> Tuple[str, Optional[float]]:
        """Classify using the optional pickled scikit-learn model."""
        model_path = settings.AI_CHATBOT_MODEL_PATH
        if not os.path.exists(model_path):
            return "", None
        try:
            import joblib

            classifier = joblib.load(model_path)
            prediction = classifier.predict([message])
            probabilities = classifier.predict_proba([message])
            confidence = float(probabilities.max())
            return str(prediction[0]), confidence
        except Exception as exc:  # never break the chat on model issues
            logger.warning("ML classification failed: %s", exc)
            return "", None

    @staticmethod
    def _keyword_classify(message: str) -> Tuple[str, float]:
        """Deterministic keyword-based intent classifier (always available)."""
        best_intent = "fallback"
        best_score = 0.0

        for intent, patterns in ChatbotService.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    score += 1
            if not patterns:
                continue
            normalized = score / len(patterns)
            if normalized > best_score:
                best_score = normalized
                best_intent = intent

        if best_score == 0:
            return "fallback", 1.0
        return best_intent, round(best_score, 2)

    # ------------------------------------------------------------------ #
    # Response generation (grounded in real data)
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_response(message: str, session: ChatSession) -> Tuple[str, str, Optional[float]]:
        """Generate a grounded bot response for ``message``."""
        intent, confidence = ChatbotService.classify_intent(message)
        user = getattr(session, "user", None)
        if user is not None and not getattr(user, "is_authenticated", False):
            user = None

        handlers = {
            "greeting": ChatbotService._respond_greeting,
            "help": ChatbotService._respond_help,
            "product_search": ChatbotService._respond_product_search,
            "recommendation": ChatbotService._respond_recommendation,
            "order_status": ChatbotService._respond_order_status,
            "review_summary": ChatbotService._respond_review_summary,
            "fallback": ChatbotService._respond_fallback,
        }
        handler = handlers.get(intent, ChatbotService._respond_fallback)
        try:
            response = handler(message, user)
        except Exception:
            logger.exception("Chatbot handler failed; using fallback.")
            response = ChatbotService._respond_fallback(message, user)

        return response, intent, confidence

    # -- Handlers ------------------------------------------------------- #
    @staticmethod
    def _respond_greeting(message: str, user: Optional[object]) -> str:
        name = ""
        if user is not None:
            name = f" {getattr(user, 'first_name', '') or getattr(user, 'username', '')}".strip()
        name_part = f", {name}" if name else ""
        return (
            f"Hello{name_part}! I'm your AI shopping assistant. I can find products, "
            "check prices and availability, recommend items, track your orders, and "
            "summarize reviews. What would you like to do?"
        )

    @staticmethod
    def _respond_help(message: str, user: Optional[object]) -> str:
        return ChatbotService.CAPABILITIES

    @staticmethod
    def _respond_product_search(message: str, user: Optional[object]) -> str:
        from apps.search.services import SearchService

        query = ChatbotService._extract_query(message)
        if not query:
            return (
                "I'd be happy to help! Please tell me what you're looking for, "
                "for example \"wireless headphones under $100\" or \"running shoes\"."
            )

        try:
            results = list(SearchService.search_products(query)[:6])
        except Exception:
            logger.debug("Postgres FTS unavailable; using semantic fallback.")
            results = []

        if not results:
            # Try a broader semantic match over the live catalog.
            try:
                from apps.ai_engine.services.ml_service import semantic_search

                hits = semantic_search(query, limit=6)
                results = [product for product, _ in hits]
            except Exception:
                results = []

        if not results:
            return (
                f"I couldn't find any products matching \"{query}\". "
                "Try different keywords, or browse all products at /products/."
            )

        lines = []
        for product in results:
            price = getattr(product, "current_price", None)
            price_txt = f"${price}" if price is not None else ""
            url = getattr(product, "get_absolute_url", lambda: f"/products/{product.slug}/")()
            availability = "In stock" if getattr(product, "stock_quantity", 0) > 0 else "Out of stock"
            lines.append(f"- {product.name} — {price_txt} ({availability}) -> {url}")

        return (
            f"Here are the best matches for \"{query}\":\n"
            + "\n".join(lines)
            + "\n\nOpen any link for full details, images and reviews."
        )

    @staticmethod
    def _respond_recommendation(message: str, user: Optional[object]) -> str:
        from apps.catalog.models import Product
        from apps.ai_engine.services.ml_service import recommend_products

        products: list = []
        if user is not None:
            try:
                products = list(recommend_products(user, limit=6))
            except Exception:
                logger.exception("Recommendation inference failed in chatbot.")
                products = []

        if not products:
            products = list(
                Product.objects.filter(is_active=True)
                .order_by("-view_count", "-average_rating")[:6]
            )

        if not products:
            return "Our catalog is empty at the moment — please check back soon!"

        lines = []
        for product in products:
            price = getattr(product, "current_price", None)
            price_txt = f"${price}" if price is not None else ""
            url = getattr(product, "get_absolute_url", lambda: f"/products/{product.slug}/")()
            lines.append(f"- {product.name} — {price_txt} -> {url}")

        if user is not None:
            lead = "Based on your activity, I'd recommend:"
        else:
            lead = "Here are some popular products shoppers love:"
        return lead + "\n" + "\n".join(lines)

    @staticmethod
    def _respond_order_status(message: str, user: Optional[object]) -> str:
        from apps.orders.models import Order

        # Try to extract an order id (UUID) from the message.
        order = None
        order_id = ChatbotService._extract_order_id(message)
        if order_id is not None:
            try:
                order = Order.objects.get(pk=order_id)
            except Order.DoesNotExist:
                order = None

        if order is not None:
            if user is not None and getattr(order, "user_id", None) not in (None, getattr(user, "pk", None)):
                return "I couldn't find that order on your account. Please check the order number."
            status = getattr(order, "status", "unknown")
            return (
                f"Order #{str(order.pk)[:8]} is currently **{status}**. "
                f"Total: ${getattr(order, 'total', 'n/a')}. "
                "Visit /orders/ for full details and history."
            )

        if user is not None:
            recent = list(Order.objects.filter(user=user).order_by("-created_at")[:5])
            if recent:
                lines = [
                    f"- #{str(o.pk)[:8]} — {getattr(o, 'status', 'unknown')}"
                    f" (${getattr(o, 'total', 'n/a')})"
                    for o in recent
                ]
                return (
                    "I couldn't find a specific order number in your message. "
                    "Here are your recent orders:\n" + "\n".join(lines)
                    + "\n\nProvide an order number for detailed tracking."
                )

        return (
            "To check an order, please log in and provide your order number "
            "(e.g. \"status of order abc123...\"). "
            "You can also view all orders at /orders/."
        )

    @staticmethod
    def _respond_review_summary(message: str, user: Optional[object]) -> str:
        from apps.catalog.models import Product
        from apps.reviews.models import Review
        from apps.ai_engine.services.ml_service import summarize_reviews

        query = ChatbotService._extract_query(message)
        product = None
        if query:
            products = list(Product.objects.filter(is_active=True, name__icontains=query)[:1])
            if products:
                product = products[0]

        if product is None:
            # Fall back to semantic search over the catalog text.
            try:
                from apps.ai_engine.services.ml_service import semantic_search

                hits = semantic_search(query or message, limit=1)
                if hits:
                    product = hits[0][0]
            except Exception:
                product = None

        if product is None:
            return (
                "I couldn't identify which product you mean. "
                "Try: \"summarize reviews for Aurora X1 Smartphone\"."
            )

        reviews = list(Review.objects.filter(product=product).values_list("body", flat=True))
        if not reviews:
            return f"No reviews yet for {product.name}. Be the first to review it!"

        summary = summarize_reviews(reviews, max_sentences=3)
        avg = None
        try:
            from django.db.models import Avg

            avg = Review.objects.filter(product=product).aggregate(avg=Avg("rating"))["avg"]
        except Exception:
            avg = None

        rating_txt = f" (avg {avg:.1f}/5)" if avg is not None else ""
        return f"Review summary for {product.name}{rating_txt}:\n{summary}"

    @staticmethod
    def _respond_fallback(message: str, user: Optional[object]) -> str:
        if (message or "").strip():
            query = ChatbotService._extract_query(message)
            # Portable fallback (works on SQLite and Postgres): semantic search
            # over the *extracted* query, so typos and filler words do not
            # defeat matching ("can you fing me a headphone" -> "headphone").
            try:
                from apps.ai_engine.services.ml_service import semantic_search

                if semantic_search(query or message, limit=5):
                    return ChatbotService._respond_product_search(message, user)
            except Exception:
                pass
            # Postgres full-text search when available.
            try:
                from apps.search.services import SearchService

                if SearchService.search_products(query or message).exists():
                    return ChatbotService._respond_product_search(message, user)
            except Exception:
                pass
        return (
            "I'm not sure I understood that. I can help you find products, "
            "check prices, get recommendations, track orders, or summarize "
            "reviews. Could you rephrase? Type \"help\" for examples."
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_query(message: str) -> str:
        """Strip command words and spell-correct to recover the product query."""
        from apps.ai_engine.text.normalizer import normalize, tokens as tokenize
        from apps.ai_engine.text.spell_corrector import default_corrector

        normalized = normalize(message)
        kept = [token for token in tokenize(normalized) if token not in _QUERY_STOP_WORDS]
        if not kept:
            kept = tokenize(normalized)
        if not kept:
            return ""
        corrected = default_corrector().correct_text(" ".join(kept))
        return corrected or " ".join(kept)

    @staticmethod
    def _extract_order_id(message: str):
        """Return a UUID order id found in ``message``, or ``None``."""
        # Full UUID.
        match = re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            (message or "").lower(),
        )
        if match:
            try:
                return uuid.UUID(match.group(0))
            except ValueError:
                return None
        return None
