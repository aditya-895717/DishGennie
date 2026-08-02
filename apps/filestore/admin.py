from django.contrib import admin

from .models import StoredFile


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'content_type', 'size', 'created_at')
    search_fields = ('name', 'content_type')
    readonly_fields = ('name', 'content_type', 'size', 'created_at')

    def has_add_permission(self, request):
        # Files arrive through uploads, never by hand.
        return False
