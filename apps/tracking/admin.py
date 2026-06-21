from django.contrib import admin
from .models import LocationUpdate

@admin.register(LocationUpdate)
class LocationUpdateAdmin(admin.ModelAdmin):
    list_display = ['booking', 'maid', 'latitude', 'longitude', 'timestamp']
