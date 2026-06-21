"""
Models for payments, wallet, subscriptions, and payouts.
"""
from django.db import models
from django.conf import settings


class Payment(models.Model):
    """Payment record for a booking."""

    class Method(models.TextChoices):
        WALLET = 'wallet', 'Wallet'
        RAZORPAY = 'razorpay', 'Razorpay'
        UPI = 'upi', 'UPI'
        COD = 'cod', 'Cash on Delivery'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    booking = models.OneToOneField('bookings.Booking', on_delete=models.CASCADE, related_name='payment')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.RAZORPAY)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.pk} - ₹{self.amount} ({self.status})"


class Wallet(models.Model):
    """User wallet for DishGennie credits."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet: {self.user.username} - ₹{self.balance}"


class WalletTransaction(models.Model):
    """Wallet transaction log."""
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=[
        ('credit', 'Credit'), ('debit', 'Debit')
    ])
    description = models.CharField(max_length=200)
    reference_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type}: ₹{self.amount}"


class Subscription(models.Model):
    """Subscription plans for customers."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=30)
    visits_per_month = models.PositiveIntegerField(default=8)
    discount_percent = models.PositiveIntegerField(default=10)
    features = models.JSONField(default=list, blank=True)
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ₹{self.price}/month"


class UserSubscription(models.Model):
    """Active user subscriptions."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    visits_remaining = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"


class MaidPayout(models.Model):
    """Weekly payout to maids."""
    maid = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    period_start = models.DateField()
    period_end = models.DateField()
    jobs_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'), ('processed', 'Processed'), ('failed', 'Failed')
    ], default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payout: {self.maid.username} - ₹{self.net_amount}"
