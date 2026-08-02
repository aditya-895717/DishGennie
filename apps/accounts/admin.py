"""
Django admin configuration for accounts.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
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
    list_display = [
        'user', 'verification_status', 'is_available', 'avg_rating',
        'total_jobs', 'hourly_rate', 'upi_id', 'aadhaar_document_link',
    ]
    list_filter = ['verification_status', 'is_available']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['aadhaar_document_link']
    fields = [
        'user', 'verification_status', 'verification_remarks', 'verified_at',
        'aadhaar_number', 'aadhaar_document', 'aadhaar_document_link',
        'police_verification', 'id_proof',
        'qr_code', 'upi_id',
        'skills', 'experience_years', 'hourly_rate', 'is_available', 'bio', 'languages',
        'avg_rating', 'total_reviews', 'total_jobs', 'total_earnings', 'profile_completion',
    ]

    def aadhaar_document_link(self, obj):
        if obj.aadhaar_document:
            return format_html('<a href="{}" target="_blank" rel="noopener">View Document</a>', obj.aadhaar_document.url)
        return 'Not uploaded'
    aadhaar_document_link.short_description = 'Aadhaar Document'
