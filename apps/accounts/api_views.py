"""
Accounts API views (DRF).
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Profile
from .serializers import ProfileSerializer


class ProfileViewSet(viewsets.ModelViewSet):
    """API endpoint for user profiles."""

    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only access their own profile."""
        return Profile.objects.filter(user=self.request.user)
