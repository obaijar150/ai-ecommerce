"""
AI Engine views: chat assistant, recommendations API.
"""

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from .services.chatbot import ChatbotService
from .services.recommendations import RecommendationService


def chat_view(request):
    """AI shopping assistant chat page."""
    return render(request, "ai_engine/chat.html")


class ChatAPIView(View):
    """Handle chat messages from the frontend."""

    def post(self, request):
        """Process a user message and return bot response."""
        message = request.POST.get("message", "").strip()
        session_key = request.session.session_key

        if not message:
            return JsonResponse({"error": "Empty message"}, status=400)

        # Get or create chat session
        session = ChatbotService.get_or_create_session(
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key,
        )

        # Save user message
        ChatbotService.save_message(session, "user", message)

        # Get bot response
        response_text, intent, confidence = ChatbotService.get_response(message, session)

        # Save bot message
        ChatbotService.save_message(session, "bot", response_text, intent, confidence)

        return JsonResponse({
            "message": response_text,
            "intent": intent,
            "confidence": float(confidence) if confidence else None,
        })


class RecommendationsAPIView(View):
    """Return AI product recommendations for the current user."""

    def get(self, request):
        """Get personalized product recommendations."""
        recommendations = RecommendationService.get_recommendations(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            limit=10,
        )

        data = [
            {
                "product_id": str(r.product.id),
                "name": r.product.name,
                "slug": r.product.slug,
                "price": str(r.product.current_price),
                "image": r.product.images.first().image.url if r.product.images.exists() else None,
                "score": float(r.score),
                "algorithm": r.algorithm,
            }
            for r in recommendations
        ]

        return JsonResponse({"recommendations": data})
