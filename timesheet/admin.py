from django.contrib import admin
from .models import Activity, Timesheet, TimesheetImage, FundsSource


@admin.register(FundsSource)
class FundsSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'activity', 'start_time', 'end_time', 'created_at']
    list_filter = ['user']
    search_fields = ['user__username', 'activity__name']


@admin.register(TimesheetImage)
class TimesheetImageAdmin(admin.ModelAdmin):
    list_display = ['timesheet', 'image', 'uploaded_at']
    search_fields = ['timesheet__user__username', 'timesheet__date']