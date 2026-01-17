from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Профиль и роль", {"fields": ("role", "fio", "department", "position", "person_status")}),
    )
    list_display = ("username", "email", "role", "fio", "department", "is_staff")
    list_filter = ("role", "department", "is_staff", "is_superuser")