from django.contrib import admin
from .models import Activity, Timesheet, FundsSource


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['name', 'code']


@admin.register(FundsSource)
class FundsSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'activity', 'hours_worked', 'submitted', 'created_at']
    list_filter = ['user', 'submitted']
    search_fields = ['user__username', 'activity__name']
