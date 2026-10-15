"""
AI Shopping Assistant chatbot service.

Uses scikit-learn for intent classification (free, open-source).
Falls back to keyword matching when ML model is unavailable.
"""

import json
import logging
import os
import re
from typing import Optional, Tuple

from django.conf import settings

from apps.ai_engine.models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


class ChatbotService:
    """Service for AI shopping assistant chatbot."""

    # Intent patterns for keyword-based fallback
    INTENT_PATTERNS = {
        "product_search": [
            r"\b(find|search|show|looking for|need|want|buy|shop for)\b.*",
            r"\bproduct|item|thing\b.*",
        ],
        "order_status": [
            r"\b(order|status|track|where is|shipping|delivery)\b.*",
            r"\bwhen.*arrive\b.*",
        ],
        "recommendation": [
            r"\b(recommend|suggest|best|top|popular|good)\b.*",
            r"\bwhat.*(buy|choose|get)\b.*",
        ],
        "greeting": [
            r"^\s*(hi|hello|hey|good morning|good afternoon)\s*$",
        ],
        "help": [
            r"\b(help|how|what can you|support|assist)\b.*",
        ],
    }

    # Response templates
    RESPONSES = {
        "greeting": "Hello! I'm your AI shopping assistant. I can help you find products, check order status, or give recommendations. What are you looking for today?",
        "product_search": "I'd be happy to help you find that! You can browse our categories or tell me more specifically what you're looking for. What type of product interests you?",
        "order_status": "To check your order status, please provide your order number (starts with #). You can also view all your orders in your account dashboard.",
        "recommendation": "Based on what's popular right now, I'd recommend checking our featured products! You can also tell me your interests and I'll suggest something tailored.",
        "help": "I can help you with:\n• Finding products\n• Order status checks\n• Product recommendations\n• General questions\n\nJust ask me anything!",
        "fallback": "I'm not sure I understand. Could you rephrase that? I can help you find products, check orders, or make recommendations.",
    }

    @staticmethod
    def get_or_create_session(user=None, session_key: Optional[str] = None):
        """Get existing active chat session or create new one."""
        # Try to find existing active session
        if user and user.is_authenticated:
            session = ChatSession.objects.filter(user=user, ended_at__isnull=True).first()
        elif session_key:
            session = ChatSession.objects.filter(
                session_key=session_key, ended_at__isnull=True
            ).first()
        else:
            session = None

        if not session:
            session = ChatSession.objects.create(
                user=user if user and user.is_authenticated else None,
                session_key=session_key if not user or not user.is_authenticated else None,
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
        """Save a chat message to the database."""
        return ChatMessage.objects.create(
            session=session,
            sender=sender,
            message=message,
            intent=intent,
            confidence=confidence,
        )

    @staticmethod
    def classify_intent(message: str) -> Tuple[str, float]:
        """
        Classify user message intent.

        Returns:
            Tuple of (intent_name, confidence_score)
        """
        message_lower = message.lower().strip()

        # Try ML classifier first
        intent, confidence = ChatbotService._ml_classify(message_lower)
        if intent and confidence and confidence > 0.6:
            return intent, confidence

        # Fallback to keyword matching
        return ChatbotService._keyword_classify(message_lower)

    @staticmethod
    def _ml_classify(message: str) -> Tuple[str, Optional[float]]:
        """Classify intent using scikit-learn model if available."""
        model_path = settings.AI_CHATBOT_MODEL_PATH

        if not os.path.exists(model_path):
            return "", None

        try:
            import joblib

            classifier = joblib.load(model_path)
            prediction = classifier.predict([message])
            probabilities = classifier.predict_proba([message])
            confidence = float(probabilities.max())

            return prediction[0], confidence

        except Exception as e:
            logger.warning(f"ML classification failed: {e}")
            return "", None

    @staticmethod
    def _keyword_classify(message: str) -> Tuple[str, float]:
        """Fallback keyword-based intent classification."""
        best_intent = "fallback"
        best_score = 0.0

        for intent, patterns in ChatbotService.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    score += 1

            normalized_score = score / len(patterns)
            if normalized_score > best_score:
                best_score = normalized_score
                best_intent = intent

        # If no patterns matched, use fallback
        if best_score == 0:
            return "fallback", 1.0

        return best_intent, round(best_score, 2)

    @staticmethod
    def get_response(message: str, session: ChatSession) -> Tuple[str, str, Optional[float]]:
        """
        Generate bot response for user message.

        Returns:
            Tuple of (response_text, intent, confidence)
        """
        intent, confidence = ChatbotService.classify_intent(message)
        response = ChatbotService.RESPONSES.get(intent, ChatbotService.RESPONSES["fallback"])

        return response, intent, confidence
