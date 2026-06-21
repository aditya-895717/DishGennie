from django.contrib import admin
from .models import Payment, Wallet, Subscription, MaidPayout

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'booking', 'amount', 'method', 'status', 'created_at']
    list_filter = ['status', 'method']

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'updated_at']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'duration_days', 'visits_per_month', 'is_active']

@admin.register(MaidPayout)
class MaidPayoutAdmin(admin.ModelAdmin):
    list_display = ['maid', 'amount', 'net_amount', 'status', 'period_start', 'period_end']
