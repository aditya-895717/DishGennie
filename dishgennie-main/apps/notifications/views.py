from rest_framework import generics, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer
from apps.accounts.permissions import IsAdmin
from apps.accounts.models import CustomUser


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)[:50]


class NotificationSummaryView(views.APIView):
    """Small unread-count payload for header badges."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.filter(user=request.user)
        return Response({
            'unread_count': queryset.filter(is_read=False).count(),
            'total_count': queryset.count(),
            'recent': NotificationSerializer(queryset[:5], many=True).data,
        })


class MarkReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        if pk:
            Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
        else:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'Marked as read.'})


class BroadcastView(views.APIView):
    """Admin broadcasts a notification to all users."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        title = request.data.get('title', '')
        message = request.data.get('message', '')
        target = request.data.get('target', 'all')  # all, customers, maids

        users = CustomUser.objects.filter(is_active=True)
        if target == 'customers':
            users = users.filter(role='customer')
        elif target == 'maids':
            users = users.filter(role='maid')

        notifications = [
            Notification(user=u, title=title, message=message, notif_type='system')
            for u in users
        ]
        Notification.objects.bulk_create(notifications)
        return Response({'message': f'Broadcast sent to {len(notifications)} users.'})
