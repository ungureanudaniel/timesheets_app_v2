from django.contrib import admin
from .models import Activity, Species, Habitat, MonitoringRecord, ActivityProgram, ActivityProgramItem, ActivityProgramSignature


class ActivityAdmin(admin.ModelAdmin):
    list_display = ('group', 'subgroup', 'name', 'code')
    list_filter = ('code',)
    search_fields = ('group', 'subgroup', 'code', 'name')


class ActivityProgramItemInline(admin.TabularInline):
    model = ActivityProgramItem
    extra = 0
    filter_horizontal = ('rangers',)


class ActivityProgramSignatureInline(admin.TabularInline):
    model = ActivityProgramSignature
    extra = 0
    fields = ('ranger', 'role', 'is_signed', 'signed_at')
    readonly_fields = ('signed_at',)


class ActivityProgramAdmin(admin.ModelAdmin):
    list_display = (
        'registration_nr',
        'registration_date',
        'year',
        'week',
        'director',
        'chief_ranger',
        'accountant',
    )
    list_filter = ('year', 'week',)
    search_fields = ('registration_nr', 'week', 'items__activity_code', 'items__activity_title',)
    filter_horizontal = ('assigned_rangers',)
    inlines = [ActivityProgramItemInline, ActivityProgramSignatureInline]

admin.site.register(Activity, ActivityAdmin)
admin.site.register(ActivityProgram, ActivityProgramAdmin)
admin.site.register(Species)
admin.site.register(Habitat)
admin.site.register(MonitoringRecord)