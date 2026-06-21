"""
Models for services & categories.
"""
from django.db import models


class City(models.Model):
    """City where DishGennie operates."""
    name = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Cities'
        ordering = ['name']

    def __str__(self):
        return f"{self.name}, {self.state}"


class ServiceCategory(models.Model):
    """Service categories offered by maids."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, default='bi-house', help_text='Bootstrap icon class')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    base_price = models.DecimalField(max_digits=8, decimal_places=2, default=299.00)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Service Categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Coupon(models.Model):
    """Discount coupons."""
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=10, choices=[
        ('percent', 'Percentage'), ('flat', 'Flat Amount')
    ])
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    min_order = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(default=100)
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code
