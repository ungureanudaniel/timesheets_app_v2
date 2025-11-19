from django.contrib import admin
from .models import Activity, Species, Habitat, MonitoringRecord


class ActivityAdmin(admin.ModelAdmin):
    list_display = ('group', 'subgroup', 'name', 'code')
    list_filter = ('code',)
    search_fields = ('group', 'subgroup', 'code', 'name')


admin.site.register(Activity, ActivityAdmin)
admin.site.register(Species)
admin.site.register(Habitat)
admin.site.register(MonitoringRecord)