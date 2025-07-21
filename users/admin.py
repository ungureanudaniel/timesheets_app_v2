from django.contrib import admin
from .models import CustomUser
from django.contrib.auth.admin import UserAdmin


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Specify what fields to show in the list display
    list_display = ['username', 'email', 'is_approved', 'is_staff', 'is_superuser']

    # Add the custom `is_approved` field in the form view
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('is_approved',)}), )  # Adding the custom field to the form
