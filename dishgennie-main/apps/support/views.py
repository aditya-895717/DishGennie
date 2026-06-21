from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import SupportTicket
from .serializers import SupportTicketSerializer
from apps.accounts.permissions import IsAdmin


class TicketListCreateView(generics.ListCreateAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_admin_user:
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_admin_user:
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=self.request.user)
