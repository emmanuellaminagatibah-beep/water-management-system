from django.contrib import admin

from .models import Delivery, Driver, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
	list_display = ('registration_number', 'capacity_litres', 'is_active')
	search_fields = ('registration_number',)
	list_filter = ('is_active',)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
	list_display = ('user', 'license_number', 'is_active')
	search_fields = ('user__username', 'user__first_name', 'user__last_name', 'license_number')
	list_filter = ('is_active',)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
	list_display = ('order', 'driver', 'vehicle', 'status', 'scheduled_date', 'delivered_at')
	search_fields = ('order__client__name', 'driver__user__username', 'vehicle__registration_number')
	list_filter = ('status', 'scheduled_date')
