from rest_framework import views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import LocationUpdate


class UpdateLocationView(views.APIView):
    """Maid sends their current location."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get('booking_id')
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        LocationUpdate.objects.create(
            booking_id=booking_id, maid=request.user,
            latitude=lat, longitude=lng,
        )
        return Response({'message': 'Location updated.'})


class GetLocationView(views.APIView):
    """Customer gets the maid's latest location."""
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        try:
            loc = LocationUpdate.objects.filter(booking_id=booking_id).latest()
            return Response({
                'latitude': str(loc.latitude),
                'longitude': str(loc.longitude),
                'timestamp': loc.timestamp.isoformat(),
            })
        except LocationUpdate.DoesNotExist:
            return Response({'error': 'No location data.'}, status=404)
