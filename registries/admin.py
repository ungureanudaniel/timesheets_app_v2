from django.contrib import admin
from pytz import timezone
from .models import RangerDocumentRegistry

@admin.register(RangerDocumentRegistry)
class RangerDocumentRegistryAdmin(admin.ModelAdmin):
    list_display = ('id', 'doc_number', 'doc_date', 'explanation', 'created_at',)
    search_fields = ('doc_number', 'explanation')
    list_filter = ('created_at')
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_at = timezone.now()
        obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)


