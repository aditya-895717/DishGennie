from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    booking = models.OneToOneField('bookings.Booking', on_delete=models.CASCADE, related_name='review')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_reviews')
    maid = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_reviews')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review: {self.customer} → {self.maid} ({self.rating}★)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update maid's average rating
        if hasattr(self.maid, 'maid_profile'):
            profile = self.maid.maid_profile
            reviews = Review.objects.filter(maid=self.maid)
            from django.db.models import Avg
            avg = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
            profile.avg_rating = round(avg, 2)
            profile.total_reviews = reviews.count()
            profile.save()
