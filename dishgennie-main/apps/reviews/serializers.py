from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'booking', 'customer', 'customer_name', 'maid', 'rating', 'comment', 'created_at']
        read_only_fields = ['customer', 'maid', 'created_at']

    def get_customer_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.username
