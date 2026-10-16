"""
Django endpoints for the integrated local AI subsystem.
"""

from __future__ import annotations

import json
from typing import Any

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.ai_engine.services.ai_integration import (
    ai_search,
    explained_recommendations,
    review_summary,
    support_answer,
)


class AISearchAPIView(View):
    """Natural-language product search with hard filters and semantic ranking."""

    def get(self, request):
        query = request.GET.get("q") or request.GET.get("query") or ""
        try:
            limit = int(request.GET.get("limit", 24))
        except (TypeError, ValueError):
            limit = 24
        constraints, results = ai_search(query, limit=limit)
        return JsonResponse(
            {
                "query": query,
                "constraints": constraints,
                "results": [
                    {
                        "product_id": str(r.product.pk),
                        "name": r.product.name,
                        "slug": r.product.slug,
                        "price": str(r.product.current_price),
                        "stock_quantity": r.product.stock_quantity,
                        "available": r.product.stock_quantity > 0,
                        "score": round(r.score, 4),
                        "reasons": r.reasons,
                        "url": f"/products/{r.product.slug}/",
                    }
                    for r in results
                ],
                "total": len(results),
            }
        )


class AIRecommendationsAPIView(View):
    """Authenticated, explainable product recommendations."""

    def get(self, request):
        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        limit = 8
        try:
            limit = int(request.GET.get("limit", 8))
        except (TypeError, ValueError):
            pass
        results = explained_recommendations(user, limit=limit)
        return JsonResponse({"recommendations": results, "user_authenticated": bool(user)})


class AIReviewSummaryAPIView(View):
    """Cached, evidence-grounded review summary for a product."""

    def get(self, request, product_id: int):
        refresh = request.GET.get("refresh") in {"1", "true", "yes"}
        try:
            payload = review_summary(product_id, refresh=refresh)
        except Exception:
            return JsonResponse({"error": "not_found"}, status=404)
        return JsonResponse(payload)


class AISupportAPIView(View):
    """Permissions-aware customer support RAG endpoint."""

    def post(self, request):
        try:
            body = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            body = {}
        query = (body.get("query") or request.POST.get("query") or "").strip()
        if not query:
            return JsonResponse({"error": "empty_query"}, status=400)
        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        result = support_answer(query, user=user)
        return JsonResponse(result)


@csrf_exempt
def ai_search_post(request):
    # Thin wrapper so the endpoint also accepts POST bodies.
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        body = {}
    query = (body.get("query") or body.get("q") or "").strip()
    try:
        limit = int(body.get("limit", 24))
    except (TypeError, ValueError):
        limit = 24
    constraints, results = ai_search(query, limit=limit)
    return JsonResponse(
        {
            "query": query,
            "constraints": constraints,
            "results": [
                {
                    "product_id": str(r.product.pk),
                    "name": r.product.name,
                    "slug": r.product.slug,
                    "price": str(r.product.current_price),
                    "stock_quantity": r.product.stock_quantity,
                    "available": r.product.stock_quantity > 0,
                    "score": round(r.score, 4),
                    "reasons": r.reasons,
                    "url": f"/products/{r.product.slug}/",
                }
                for r in results
            ],
            "total": len(results),
        }
    )
