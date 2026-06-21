"""
Models for booking lifecycle.
"""
import random
from decimal import Decimal
from django.db import models
from django.conf import settings


class Booking(models.Model):
    """Core booking model."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        MAID_EN_ROUTE = 'en_route', 'Maid En Route'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        DISPUTED = 'disputed', 'Disputed'

    class BookingType(models.TextChoices):
        INSTANT = 'instant', 'Instant'
        SCHEDULED = 'scheduled', 'Scheduled'

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_bookings'
    )
    maid = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='maid_jobs',
        null=True, blank=True
    )
    service = models.ForeignKey(
        'services.ServiceCategory', on_delete=models.CASCADE, related_name='bookings'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    booking_type = models.CharField(max_length=15, choices=BookingType.choices, default=BookingType.INSTANT)
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)

    # Location
    address = models.TextField()
    city = models.ForeignKey('services.City', on_delete=models.SET_NULL, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Service details
    duration_hours = models.DecimalField(max_digits=4, decimal_places=1, default=2.0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    special_instructions = models.TextField(blank=True)

    # Verification
    otp = models.CharField(max_length=6, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking #{self.pk} - {self.customer} → {self.service}"

    def save(self, *args, **kwargs):
        if not self.otp:
            self.otp = str(random.randint(100000, 999999))
        if not self.final_amount:
            self.final_amount = Decimal(str(self.total_amount or 0)) - Decimal(str(self.discount_amount or 0))
        super().save(*args, **kwargs)
