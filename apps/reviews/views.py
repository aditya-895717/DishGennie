from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Review
from .serializers import ReviewSerializer
from apps.bookings.models import Booking


class ReviewCreateView(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        booking = Booking.objects.get(pk=self.request.data.get('booking'), customer=self.request.user)
        serializer.save(customer=self.request.user, maid=booking.maid)


class MaidReviewsView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        maid_id = self.kwargs.get('maid_id')
        return Review.objects.filter(maid_id=maid_id)
