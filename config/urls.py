"""
Root URL configuration for AI E-Commerce Platform.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.catalog.urls", namespace="catalog")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("orders/", include("apps.orders.urls", namespace="orders")),
    path("reviews/", include("apps.reviews.urls", namespace="reviews")),
    path("search/", include("apps.search.urls", namespace="search")),
    path("chat/", include("apps.ai_engine.urls", namespace="ai_engine")),
    path("analytics/", include("apps.analytics.urls", namespace="analytics")),
    path("api/", include("apps.catalog.api_urls", namespace="api_catalog")),
    path("api/", include("apps.accounts.api_urls", namespace="api_accounts")),
    path("api/", include("apps.orders.api_urls", namespace="api_orders")),
    path("api/", include("apps.reviews.api_urls", namespace="api_reviews")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

# Custom error handlers
handler404 = "apps.catalog.views.page_not_found"
handler500 = "apps.catalog.views.server_error"
