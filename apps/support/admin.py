from django.contrib import admin
from .models import SupportTicket, TicketMessage

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'user', 'priority', 'status', 'created_at']
    list_filter = ['priority', 'status']

@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'sender', 'created_at']
