from django.contrib import admin
from .models import City, ServiceCategory, Coupon

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'state', 'is_active']
    list_filter = ['state', 'is_active']

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_price', 'is_active', 'sort_order']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'used_count', 'usage_limit', 'is_active']
