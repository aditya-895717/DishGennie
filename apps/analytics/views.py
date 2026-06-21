"""
Admin dashboard analytics API views.
"""
from rest_framework import views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsAdmin
from apps.accounts.models import CustomUser, MaidProfile
from apps.bookings.models import Booking
from apps.payments.models import Payment
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta


class AdminDashboardView(views.APIView):
    """Main admin dashboard KPIs."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)
        week_ago = today - timedelta(days=7)

        total_users = CustomUser.objects.filter(role='customer').count()
        total_maids = CustomUser.objects.filter(role='maid').count()
        active_bookings = Booking.objects.filter(
            status__in=['pending', 'accepted', 'en_route', 'in_progress']
        ).count()
        total_bookings = Booking.objects.count()
        completed_bookings = Booking.objects.filter(status='completed').count()

        total_revenue = Payment.objects.filter(
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        today_revenue = Payment.objects.filter(
            status='completed', completed_at__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0

        monthly_revenue = Payment.objects.filter(
            status='completed', completed_at__date__gte=month_ago
        ).aggregate(total=Sum('amount'))['total'] or 0

        pending_verifications = MaidProfile.objects.filter(
            verification_status='pending'
        ).count()

        new_users_week = CustomUser.objects.filter(
            created_at__date__gte=week_ago
        ).count()

        return Response({
            'total_users': total_users,
            'total_maids': total_maids,
            'active_bookings': active_bookings,
            'total_bookings': total_bookings,
            'completed_bookings': completed_bookings,
            'total_revenue': str(total_revenue),
            'today_revenue': str(today_revenue),
            'monthly_revenue': str(monthly_revenue),
            'pending_verifications': pending_verifications,
            'new_users_week': new_users_week,
        })


class RevenueChartView(views.APIView):
    """Revenue data for last 30 days."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        today = timezone.now().date()
        data = []
        for i in range(30):
            date = today - timedelta(days=29 - i)
            revenue = Payment.objects.filter(
                status='completed', completed_at__date=date
            ).aggregate(total=Sum('amount'))['total'] or 0
            bookings = Booking.objects.filter(created_at__date=date).count()
            data.append({
                'date': date.isoformat(),
                'revenue': float(revenue),
                'bookings': bookings,
            })
        return Response(data)


class CityAnalyticsView(views.APIView):
    """City-wise analytics."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.services.models import City
        cities = City.objects.filter(is_active=True)
        data = []
        for city in cities:
            bookings = Booking.objects.filter(city=city).count()
            revenue = Payment.objects.filter(
                booking__city=city, status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            maids = CustomUser.objects.filter(role='maid', city=city).count()
            data.append({
                'city': city.name,
                'bookings': bookings,
                'revenue': float(revenue),
                'maids': maids,
            })
        return Response(data)


class ServiceAnalyticsView(views.APIView):
    """Service category performance."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.services.models import ServiceCategory
        categories = ServiceCategory.objects.filter(is_active=True)
        data = []
        for cat in categories:
            count = Booking.objects.filter(service=cat).count()
            revenue = Payment.objects.filter(
                booking__service=cat, status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            data.append({
                'service': cat.name,
                'icon': cat.icon,
                'bookings': count,
                'revenue': float(revenue),
            })
        return Response(data)
