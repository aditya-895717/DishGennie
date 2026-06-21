"""
Django admin configuration for accounts.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, MaidProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_verified', 'created_at']
    list_filter = ['role', 'is_verified', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    fieldsets = UserAdmin.fieldsets + (
        ('DishGennie Fields', {
            'fields': ('role', 'phone', 'avatar', 'city', 'address',
                       'latitude', 'longitude', 'is_verified',
                       'referral_code', 'referred_by', 'date_of_birth')
        }),
    )


@admin.register(MaidProfile)
class MaidProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'verification_status', 'is_available', 'avg_rating', 'total_jobs', 'hourly_rate']
    list_filter = ['verification_status', 'is_available']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
