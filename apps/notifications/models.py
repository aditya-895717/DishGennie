from django.db import models
from django.conf import settings


class Notification(models.Model):
    class NotifType(models.TextChoices):
        BOOKING = 'booking', 'Booking'
        PAYMENT = 'payment', 'Payment'
        SYSTEM = 'system', 'System'
        PROMO = 'promo', 'Promotional'
        ALERT = 'alert', 'Alert'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notif_type = models.CharField(max_length=20, choices=NotifType.choices, default=NotifType.SYSTEM)
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} → {self.user.username}"
