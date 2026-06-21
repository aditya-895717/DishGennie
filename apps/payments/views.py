"""
Views for payments app.
"""
from decimal import Decimal
from datetime import timedelta
from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Payment, Wallet, WalletTransaction, Subscription, UserSubscription, MaidPayout
from .serializers import (
    PaymentSerializer, WalletSerializer, WalletTransactionSerializer,
    SubscriptionSerializer, MaidPayoutSerializer,
)
from apps.accounts.permissions import IsAdmin, IsMaid


class PaymentInitiateView(views.APIView):
    """Initiate a payment for a booking."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get('booking_id')
        method = request.data.get('method', 'razorpay')
        amount = request.data.get('amount', 0)

        payment = Payment.objects.create(
            booking_id=booking_id,
            user=request.user,
            amount=amount,
            method=method,
        )

        if method == 'razorpay':
            # In production, create Razorpay order here
            payment.razorpay_order_id = f"order_demo_{payment.pk}"
            payment.save()

        return Response({
            'payment_id': payment.pk,
            'razorpay_order_id': payment.razorpay_order_id,
            'amount': str(payment.amount),
        })


class PaymentVerifyView(views.APIView):
    """Verify payment completion."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get('payment_id')
        try:
            payment = Payment.objects.get(pk=payment_id, user=request.user)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found.'}, status=404)

        from django.utils import timezone
        payment.status = 'completed'
        payment.razorpay_payment_id = request.data.get('razorpay_payment_id', '')
        payment.completed_at = timezone.now()
        payment.save()
        return Response({'message': 'Payment verified!', 'status': 'completed'})


class WalletView(views.APIView):
    """Get wallet balance."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        transactions = WalletTransaction.objects.filter(wallet=wallet)[:20]
        return Response({
            'balance': str(wallet.balance),
            'transactions': WalletTransactionSerializer(transactions, many=True).data,
        })


class WalletAddView(views.APIView):
    """Add money to wallet."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get('amount', 0)
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount.'}, status=400)

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet.balance += amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type='credit',
            description='Added to wallet',
        )
        return Response({'message': f'₹{amount} added!', 'balance': str(wallet.balance)})


class SubscriptionListView(generics.ListAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    queryset = Subscription.objects.filter(is_active=True)


class SubscribeView(views.APIView):
    """Create or replace the customer's active subscription."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get('plan_id')
        try:
            plan = Subscription.objects.get(pk=plan_id, is_active=True)
        except Subscription.DoesNotExist:
            return Response({'error': 'Subscription plan not found.'}, status=404)

        today = timezone.now().date()
        UserSubscription.objects.filter(user=request.user, is_active=True).update(is_active=False)
        subscription = UserSubscription.objects.create(
            user=request.user,
            plan=plan,
            start_date=today,
            end_date=today + timedelta(days=plan.duration_days),
            visits_remaining=plan.visits_per_month,
            is_active=True,
        )
        return Response({
            'message': f'{plan.name} plan activated.',
            'subscription_id': subscription.pk,
            'plan': plan.name,
            'end_date': subscription.end_date.isoformat(),
            'visits_remaining': subscription.visits_remaining,
        }, status=status.HTTP_201_CREATED)


class MaidEarningsView(views.APIView):
    """Maid earnings summary."""
    permission_classes = [IsAuthenticated, IsMaid]

    def get(self, request):
        from apps.bookings.models import Booking
        from django.db.models import Sum, Count
        from django.utils import timezone
        from datetime import timedelta

        user = request.user
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        completed = Booking.objects.filter(maid=user, status='completed')

        today_earnings = completed.filter(
            completed_at__date=today
        ).aggregate(total=Sum('final_amount'))['total'] or 0

        weekly_earnings = completed.filter(
            completed_at__date__gte=week_ago
        ).aggregate(total=Sum('final_amount'))['total'] or 0

        monthly_earnings = completed.filter(
            completed_at__date__gte=month_ago
        ).aggregate(total=Sum('final_amount'))['total'] or 0

        total_jobs = completed.count()

        payouts = MaidPayout.objects.filter(maid=user).order_by('-created_at')[:10]

        return Response({
            'today': str(today_earnings),
            'weekly': str(weekly_earnings),
            'monthly': str(monthly_earnings),
            'total_jobs': total_jobs,
            'payouts': MaidPayoutSerializer(payouts, many=True).data,
        })


class AdminPaymentReportsView(views.APIView):
    """Admin payment reports."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from django.db.models import Sum, Count
        total_revenue = Payment.objects.filter(status='completed').aggregate(
            total=Sum('amount'))['total'] or 0
        total_payments = Payment.objects.count()
        pending_payouts = MaidPayout.objects.filter(status='pending').aggregate(
            total=Sum('net_amount'))['total'] or 0

        return Response({
            'total_revenue': str(total_revenue),
            'total_payments': total_payments,
            'pending_payouts': str(pending_payouts),
        })


class AdminPaymentListView(generics.ListAPIView):
    """Recent payment transactions for the admin payment screen."""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return Payment.objects.select_related('user', 'booking').order_by('-created_at')[:100]
