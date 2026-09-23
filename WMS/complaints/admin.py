from django.contrib import admin

from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
	list_display = ('subject', 'client', 'status', 'priority', 'assigned_to', 'created_at')
	search_fields = ('subject', 'client__name', 'description')
	list_filter = ('status', 'priority', 'created_at')
