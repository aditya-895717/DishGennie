from django.db import models
from django.conf import settings


class LocationUpdate(models.Model):
    """Stores maid location updates during active bookings."""
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, related_name='locations')
    maid = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        get_latest_by = 'timestamp'

    def __str__(self):
        return f"Location: {self.maid.username} @ {self.timestamp}"
