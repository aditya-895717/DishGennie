from rest_framework import serializers
from .models import SupportTicket, TicketMessage

class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    class Meta:
        model = TicketMessage
        fields = ['id', 'sender', 'sender_name', 'message', 'attachment', 'created_at']
        read_only_fields = ['sender']

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username

class SupportTicketSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = ['id', 'user', 'user_name', 'booking', 'subject', 'description',
                  'priority', 'status', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['user']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
