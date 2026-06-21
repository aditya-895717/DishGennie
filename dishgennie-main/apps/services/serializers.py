"""
Serializers for services app.
"""
from rest_framework import serializers
from .models import City, ServiceCategory, Coupon


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'state', 'is_active']


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'slug', 'icon', 'description', 'image', 'base_price', 'is_active']


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'description', 'discount_type', 'discount_value',
                  'min_order', 'max_discount', 'valid_from', 'valid_until', 'is_active']
