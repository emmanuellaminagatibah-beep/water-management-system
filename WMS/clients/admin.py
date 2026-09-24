from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
	list_display = (
		'client_id',
		'business_name',
		'phone',
		'category',
		'status',
		'created_at',
	)
	search_fields = (
		'client_id',
		'business_name',
		'phone',
		'email',
	)
	list_filter = ('category', 'status')
