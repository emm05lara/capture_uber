from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = [
        "username", "email", "first_name", "last_name",
        "rol", "is_staff", "is_active",
    ]
    list_filter = ["rol", "is_staff", "is_active", "groups"]
    fieldsets = UserAdmin.fieldsets + (
        ("Rol en el sistema", {"fields": ("rol",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Rol en el sistema", {"fields": ("rol",)}),
    )
