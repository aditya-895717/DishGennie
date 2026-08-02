"""
Serializers for bookings app.
"""
from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    maid_name = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()
    maid_qr_code = serializers.SerializerMethodField()
    maid_upi_id = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'customer_name', 'maid', 'maid_name',
            'service', 'service_name', 'status', 'booking_type',
            'scheduled_date', 'scheduled_time',
            'address', 'city', 'latitude', 'longitude',
            'duration_hours', 'total_amount', 'discount_amount', 'final_amount',
            'special_instructions', 'otp', 'otp_verified_at',
            'created_at', 'updated_at', 'accepted_at', 'started_at', 'completed_at',
            'cancelled_at', 'cancellation_reason',
            'maid_qr_code', 'maid_upi_id',
            'payment_status', 'payment_method',
        ]
        read_only_fields = [
            'customer', 'otp', 'otp_verified_at', 'created_at', 'updated_at',
            'accepted_at', 'started_at', 'completed_at', 'cancelled_at',
            'cancellation_reason',
        ]

    def get_customer_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.username

    def get_maid_name(self, obj):
        return (obj.maid.get_full_name() or obj.maid.username) if obj.maid else ''

    def get_service_name(self, obj):
        return obj.service.name if obj.service else ''

    def _maid_profile(self, obj):
        return getattr(obj.maid, 'maid_profile', None) if obj.maid else None

    def get_maid_qr_code(self, obj):
        profile = self._maid_profile(obj)
        if profile and profile.qr_code:
            request = self.context.get('request')
            return request.build_absolute_uri(profile.qr_code.url) if request else profile.qr_code.url
        return None

    def get_maid_upi_id(self, obj):
        profile = self._maid_profile(obj)
        return profile.upi_id if profile else None

    def _payment(self, obj):
        # Payment is a reverse OneToOne — absent until someone initiates or
        # the maid confirms, so this must not assume it exists.
        return getattr(obj, 'payment', None)

    def get_payment_status(self, obj):
        payment = self._payment(obj)
        return payment.status if payment else None

    def get_payment_method(self, obj):
        payment = self._payment(obj)
        return payment.method if payment else None


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            'id', 'service', 'booking_type', 'scheduled_date', 'scheduled_time',
            'address', 'city', 'latitude', 'longitude',
            'duration_hours', 'total_amount', 'special_instructions', 'maid',
        ]
        read_only_fields = ['id']
