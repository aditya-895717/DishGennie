from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'maid', 'service', 'status', 'booking_type', 'final_amount', 'created_at']
    list_filter = ['status', 'booking_type', 'created_at']
    search_fields = ['customer__username', 'maid__username']
    readonly_fields = ['otp', 'created_at']
