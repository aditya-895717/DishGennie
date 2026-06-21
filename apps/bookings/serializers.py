"""
Serializers for bookings app.
"""
from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    maid_name = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'customer_name', 'maid', 'maid_name',
            'service', 'service_name', 'status', 'booking_type',
            'scheduled_date', 'scheduled_time',
            'address', 'city', 'latitude', 'longitude',
            'duration_hours', 'total_amount', 'discount_amount', 'final_amount',
            'special_instructions', 'otp',
            'created_at', 'accepted_at', 'started_at', 'completed_at',
            'cancelled_at', 'cancellation_reason',
        ]
        read_only_fields = [
            'customer', 'otp', 'created_at', 'accepted_at', 'started_at',
            'completed_at', 'cancelled_at', 'cancellation_reason',
        ]

    def get_customer_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.username

    def get_maid_name(self, obj):
        return (obj.maid.get_full_name() or obj.maid.username) if obj.maid else ''

    def get_service_name(self, obj):
        return obj.service.name if obj.service else ''


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            'id', 'service', 'booking_type', 'scheduled_date', 'scheduled_time',
            'address', 'city', 'latitude', 'longitude',
            'duration_hours', 'total_amount', 'special_instructions', 'maid',
        ]
        read_only_fields = ['id']
