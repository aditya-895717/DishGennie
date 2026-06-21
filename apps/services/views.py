"""
Views for services app.
"""
from rest_framework import generics
from rest_framework.permissions import AllowAny
from .models import City, ServiceCategory
from .serializers import CitySerializer, ServiceCategorySerializer


class CityListView(generics.ListAPIView):
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    queryset = City.objects.filter(is_active=True)


class ServiceCategoryListView(generics.ListAPIView):
    serializer_class = ServiceCategorySerializer
    permission_classes = [AllowAny]
    queryset = ServiceCategory.objects.filter(is_active=True)
