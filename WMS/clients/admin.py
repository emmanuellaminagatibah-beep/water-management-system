from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
	list_display = ('name', 'email', 'phone', 'is_active', 'created_at')
	search_fields = ('name', 'email', 'phone')
	list_filter = ('is_active',)
