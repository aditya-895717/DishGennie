from rest_framework import serializers
from .models import Payment, Wallet, WalletTransaction, Subscription, UserSubscription, MaidPayout


class PaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    booking_code = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'completed_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_booking_code(self, obj):
        return f'DG{obj.booking_id:05d}' if obj.booking_id else ''


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = '__all__'


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionSerializer(read_only=True)

    class Meta:
        model = UserSubscription
        fields = '__all__'


class MaidPayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaidPayout
        fields = '__all__'
