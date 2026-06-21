"""
Accounts App — Custom User model with role-based access.
"""
import uuid
import random
import string
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


def generate_referral_code():
    """Generate a unique 8-character referral code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class CustomUser(AbstractUser):
    """Extended User model with role-based access control."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MAID = 'maid', 'Maid'
        CUSTOMER = 'customer', 'Customer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=15, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    city = models.ForeignKey(
        'services.City', on_delete=models.SET_NULL, null=True, blank=True, related_name='users'
    )
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=10, unique=True, default=generate_referral_code)
    referred_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_staff or self.is_superuser

    @property
    def is_maid_user(self):
        return self.role == self.Role.MAID

    @property
    def is_customer_user(self):
        return self.role == self.Role.CUSTOMER


class MaidProfile(models.Model):
    """Extended profile for maid/service provider users."""

    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        UNDER_REVIEW = 'under_review', 'Under Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='maid_profile'
    )
    aadhaar_number = models.CharField(max_length=12, blank=True)
    aadhaar_document = models.FileField(upload_to='documents/aadhaar/', blank=True, null=True)
    police_verification = models.FileField(upload_to='documents/police/', blank=True, null=True)
    id_proof = models.FileField(upload_to='documents/id/', blank=True, null=True)
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    verification_remarks = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    skills = models.ManyToManyField('services.ServiceCategory', blank=True, related_name='maids')
    experience_years = models.PositiveIntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=200.00)
    is_available = models.BooleanField(default=True)
    bio = models.TextField(blank=True)
    languages = models.CharField(max_length=200, blank=True, help_text='Comma-separated languages')
    avg_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.PositiveIntegerField(default=0)
    total_jobs = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    profile_completion = models.PositiveIntegerField(default=0)  # Percentage

    class Meta:
        verbose_name = 'Maid Profile'
        verbose_name_plural = 'Maid Profiles'

    def __str__(self):
        return f"Maid: {self.user.get_full_name() or self.user.username}"

    def calculate_completion(self):
        """Calculate profile completion percentage."""
        fields = [
            bool(self.user.first_name), bool(self.user.last_name),
            bool(self.user.phone), bool(self.user.avatar),
            bool(self.aadhaar_number), bool(self.aadhaar_document),
            bool(self.bio), bool(self.languages),
            self.skills.exists(), self.experience_years > 0,
        ]
        self.profile_completion = int(sum(fields) / len(fields) * 100)
        return self.profile_completion
