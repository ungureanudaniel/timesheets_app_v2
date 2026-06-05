from django.contrib import admin
from .models import CustomUser
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Specify what fields to show in the list display
    list_display = ['username', 'email', 'is_approved', 'is_staff', 'is_superuser', 'bio', 'job_title', 'resume', 'avatar']
    search_fields = UserAdmin.search_fields + ('job_title',)
    # Add the custom `is_approved` field in the form view
    fieldsets = tuple(UserAdmin.fieldsets) + (
        (_('Profile Information'), {
            'fields': ('job_title', 'role', 'is_approved', 'is_person', 'bio', 'avatar', 'resume')
        }),
    )


