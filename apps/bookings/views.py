"""
Views for bookings app.
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Booking
from .serializers import BookingSerializer, BookingCreateSerializer
from apps.accounts.permissions import IsCustomer, IsMaid, IsAdmin
from apps.notifications.models import Notification
from apps.accounts.email_utils import (
    send_otp_email,
    send_booking_confirmation,
    send_maid_notification,
)

logger = logging.getLogger(__name__)


def _notify(user, title, message, notif_type='booking', action_url=''):
    if user:
        try:
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notif_type=notif_type,
                action_url=action_url,
            )
        except Exception as exc:
            logger.warning("Notification failed for user %s: %s", getattr(user, 'pk', user), exc)


def _check_maid_availability(maid, scheduled_date):
    """Return True when the maid has no conflicting active booking on scheduled_date."""
    if not maid or not scheduled_date:
        return True
    return not Booking.objects.filter(
        maid=maid,
        scheduled_date=scheduled_date,
        status__in=[
            Booking.Status.PENDING,
            Booking.Status.ACCEPTED,
            Booking.Status.MAID_EN_ROUTE,
            Booking.Status.IN_PROGRESS,
        ],
    ).exists()


class BookingListCreateView(generics.ListCreateAPIView):
    """List own bookings or create a new booking (customer)."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BookingCreateSerializer
        return BookingSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user:
            return Booking.objects.all()
        if user.is_customer_user:
            return Booking.objects.filter(customer=user)
        elif user.is_maid_user:
            return Booking.objects.filter(maid=user)
        return Booking.objects.none()

    def create(self, request, *args, **kwargs):
        if not request.user.is_customer_user or request.user.is_admin_user:
            raise PermissionDenied('Only customers can create bookings.')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        maid = serializer.validated_data.get('maid')
        scheduled_date = serializer.validated_data.get('scheduled_date')

        # Maid availability check — before any DB write
        if not _check_maid_availability(maid, scheduled_date):
            return Response(
                {'error': 'This maid is not available on the requested date. Please choose another maid or date.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Wallet balance check — only when caller explicitly selects wallet payment
        payment_method = request.data.get('payment_method', '')
        if payment_method == 'wallet':
            total_amount = Decimal(str(serializer.validated_data.get('total_amount', 0) or 0))
            try:
                from apps.payments.models import Wallet
                wallet = Wallet.objects.get(user=request.user)
                if wallet.balance < total_amount:
                    return Response(
                        {
                            'error': (
                                f'Insufficient wallet balance. '
                                f'Available: ₹{wallet.balance}, Required: ₹{total_amount}'
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except Exception as exc:
                logger.warning("Wallet check skipped for user %s: %s", request.user.pk, exc)

        with transaction.atomic():
            booking = serializer.save(customer=request.user)
            auto_accepted = False
            if booking.maid_id and booking.status == Booking.Status.PENDING:
                booking.status = Booking.Status.ACCEPTED
                booking.accepted_at = timezone.now()
                booking.save(update_fields=['status', 'accepted_at'])
                auto_accepted = True

        # Post-creation side-effects — never raise; booking is already committed
        try:
            if auto_accepted:
                _notify(
                    booking.maid,
                    'New booking assigned',
                    f'Booking #{booking.pk} has been assigned to you.',
                    action_url=f'/maid-panel/navigation/?booking_id={booking.pk}',
                )
                _notify(
                    booking.customer,
                    'Booking confirmed',
                    f'Your booking #{booking.pk} has been accepted.',
                    action_url=f'/live-tracking/{booking.pk}/',
                )
            else:
                _notify(
                    booking.customer,
                    'Booking created',
                    f'Your booking #{booking.pk} is waiting for a maid.',
                    action_url='/my-bookings/',
                )
        except Exception as exc:
            logger.warning("Post-booking notifications failed for booking #%s: %s", booking.pk, exc)

        try:
            send_otp_email(
                booking.customer.email,
                booking.otp,
                booking.customer.first_name or booking.customer.username,
            )
            send_booking_confirmation(
                booking.customer.email,
                booking,
                booking.customer.first_name or booking.customer.username,
            )
            if booking.maid:
                send_maid_notification(
                    booking.maid.email,
                    booking,
                    booking.maid.first_name or booking.maid.username,
                )
        except Exception as exc:
            logger.warning("Post-booking emails failed for booking #%s: %s", booking.pk, exc)

        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailView(generics.RetrieveUpdateAPIView):
    """Booking detail and update."""
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user:
            return Booking.objects.all()
        return Booking.objects.filter(customer=user) | Booking.objects.filter(maid=user)


class AcceptBookingView(views.APIView):
    """Maid accepts a booking."""
    permission_classes = [IsAuthenticated, IsMaid]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, status=Booking.Status.PENDING)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found or already accepted.'}, status=404)
        booking.maid = request.user
        booking.status = Booking.Status.ACCEPTED
        booking.accepted_at = timezone.now()
        booking.save()
        _notify(
            booking.customer,
            'Booking accepted',
            f'{request.user.get_full_name() or request.user.username} accepted booking #{booking.pk}.',
            action_url=f'/live-tracking/{booking.pk}/',
        )
        return Response({'message': 'Booking accepted!', 'booking': BookingSerializer(booking).data})


class RejectBookingView(views.APIView):
    """Maid rejects a booking."""
    permission_classes = [IsAuthenticated, IsMaid]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, maid=request.user)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=404)
        booking.status = Booking.Status.PENDING
        booking.maid = None
        booking.save()
        return Response({'message': 'Booking rejected.'})


class EnRouteBookingView(views.APIView):
    """Maid marks an accepted booking as en route."""
    permission_classes = [IsAuthenticated, IsMaid]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, maid=request.user, status=Booking.Status.ACCEPTED)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found or cannot be marked en route.'}, status=404)
        booking.status = Booking.Status.MAID_EN_ROUTE
        booking.save(update_fields=['status'])
        _notify(
            booking.customer,
            'Maid is en route',
            f'Your maid is on the way for booking #{booking.pk}.',
            action_url=f'/live-tracking/{booking.pk}/',
        )
        return Response({'message': 'Maid is en route.', 'booking': BookingSerializer(booking).data})


class StartBookingView(views.APIView):
    """Maid starts service (OTP verification)."""
    permission_classes = [IsAuthenticated, IsMaid]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(
                pk=pk,
                maid=request.user,
                status__in=[Booking.Status.ACCEPTED, Booking.Status.MAID_EN_ROUTE],
            )
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=404)

        otp = request.data.get('otp', '')
        if otp != booking.otp:
            return Response({'error': 'Invalid OTP.'}, status=400)

        now = timezone.now()
        booking.status = Booking.Status.IN_PROGRESS
        booking.started_at = now
        booking.otp_verified_at = now
        booking.save()
        _notify(
            booking.customer,
            'Service started',
            f'Booking #{booking.pk} has started.',
            action_url=f'/live-tracking/{booking.pk}/',
        )
        return Response({'message': 'Service started!'})


class CompleteBookingView(views.APIView):
    """Maid completes service."""
    permission_classes = [IsAuthenticated, IsMaid]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, maid=request.user, status=Booking.Status.IN_PROGRESS)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=404)

        with transaction.atomic():
            booking.status = Booking.Status.COMPLETED
            booking.completed_at = timezone.now()
            booking.save()
            if hasattr(request.user, 'maid_profile'):
                from apps.accounts.models import MaidProfile
                MaidProfile.objects.filter(user=request.user).update(
                    total_jobs=F('total_jobs') + 1,
                    total_earnings=F('total_earnings') + booking.final_amount,
                )

        _notify(
            booking.customer,
            'Service completed',
            f'Booking #{booking.pk} is complete.',
            action_url='/my-bookings/',
        )
        return Response({'message': 'Service completed!', 'booking': BookingSerializer(booking).data})


class CancelBookingView(views.APIView):
    """Customer cancels a booking."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(
                pk=pk,
                customer=request.user,
                status__in=[Booking.Status.PENDING, Booking.Status.ACCEPTED],
            )
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found or cannot be cancelled.'}, status=404)
        booking.status = Booking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.cancellation_reason = request.data.get('reason', '')
        booking.save()
        _notify(
            booking.customer,
            'Booking cancelled',
            f'Booking #{booking.pk} has been cancelled.',
            action_url='/my-bookings/',
        )
        _notify(
            booking.maid,
            'Booking cancelled',
            f'Booking #{booking.pk} was cancelled by the customer.',
            action_url='/maid-panel/jobs/',
        )
        return Response({'message': 'Booking cancelled.'})


class MaidPendingRequestsView(generics.ListAPIView):
    """List pending bookings for maids to accept."""
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated, IsMaid]

    def get_queryset(self):
        return Booking.objects.filter(status=Booking.Status.PENDING).order_by('-created_at')


class MaidActiveJobsView(generics.ListAPIView):
    """List active jobs for a maid."""
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated, IsMaid]

    def get_queryset(self):
        return Booking.objects.filter(
            maid=self.request.user,
            status__in=[Booking.Status.ACCEPTED, Booking.Status.MAID_EN_ROUTE, Booking.Status.IN_PROGRESS],
        )
