from django.contrib import admin
from .models import RangerDocumentRegistry

@admin.register(RangerDocumentRegistry)
class RangerDocumentRegistryAdmin(admin.ModelAdmin):
    list_display = ('id', 'doc_number', 'doc_date', 'explanation', 'created_at',)
    search_fields = ('doc_number', 'explanation',)
    list_filter = ('created_at',)


