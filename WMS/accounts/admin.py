from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User    


@admin.register(User)
class CustomUserAdmin(UserAdmin):
	fieldsets = UserAdmin.fieldsets + (
		('Water management profile', {'fields': ('role', 'phone')}),
	)
	add_fieldsets = UserAdmin.add_fieldsets + (
		('Water management profile', {'fields': ('role', 'phone')}),
	)
	list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
	list_filter = ('role', 'is_staff', 'is_active')
	search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')