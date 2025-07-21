from django.contrib import admin
from .models import MonthlyReport


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = ['user', 'description', 'timeframe', 'date', 'hours']
    list_filter = ['user', 'date']
    search_fields = ['user__username', 'timeframe']
