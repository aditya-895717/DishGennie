from django.utils import timezone
from rest_framework import views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.models import MaidProfile
from apps.accounts.permissions import IsMaid
from apps.bookings.models import Booking
from .models import LocationUpdate


class UpdateLocationView(views.APIView):
    """Maid sends their current location.

    Writes a LocationUpdate history row *and* denormalises the fix onto the
    maid's profile (current_lat/current_lng/last_location_update) so that
    "maids near me" can filter on a single indexed table.
    """
    permission_classes = [IsAuthenticated, IsMaid]

    def post(self, request):
        booking_id = request.data.get('booking_id')
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')

        try:
            booking = Booking.objects.get(pk=booking_id)
        except (Booking.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Booking not found.'}, status=404)

        if booking.maid_id != request.user.pk:
            return Response({'error': 'You are not assigned to this booking.'}, status=403)

        update = LocationUpdate.objects.create(
            booking=booking, maid=request.user,
            latitude=lat, longitude=lng,
        )

        MaidProfile.objects.filter(user=request.user).update(
            current_lat=update.latitude,
            current_lng=update.longitude,
            last_location_update=update.timestamp or timezone.now(),
        )

        return Response({'message': 'Location updated.'})


class GetLocationView(views.APIView):
    """Customer polls for the maid's latest location.

    Returns 200 with null coordinates when no fix has arrived yet, rather
    than a 404 — "not there yet" is the normal state at the start of a
    booking, not an error, and the page polls this every few seconds.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        try:
            booking = Booking.objects.get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=404)

        if booking.customer_id != request.user.pk and booking.maid_id != request.user.pk:
            return Response({'error': 'You do not have access to this booking.'}, status=403)

        payload = {
            'booking_id': booking.pk,
            'maid_status': booking.status,
            'lat': None,
            'lng': None,
            'updated_at': None,
            # Legacy key names kept so any older client keeps working.
            'latitude': None,
            'longitude': None,
            'timestamp': None,
        }

        # -id breaks ties: two pings can land in the same clock tick, and
        # timestamp alone then picks an arbitrary one of them.
        loc = (
            LocationUpdate.objects
            .filter(booking_id=booking.pk)
            .order_by('-timestamp', '-id')
            .first()
        )
        if loc is not None:
            timestamp = loc.timestamp.isoformat()
            payload.update({
                'lat': str(loc.latitude),
                'lng': str(loc.longitude),
                'updated_at': timestamp,
                'latitude': str(loc.latitude),
                'longitude': str(loc.longitude),
                'timestamp': timestamp,
            })

        return Response(payload)
