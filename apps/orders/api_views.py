"""
Orders API views (DRF).
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Order
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    """API endpoint for orders."""

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only access their own orders."""
        return Order.objects.filter(user=self.request.user)
