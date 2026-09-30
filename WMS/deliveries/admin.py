from django.contrib import admin

from .models import Delivery, Driver, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
	list_display = ('registration_number', 'vehicle_type', 'capacity_litres', 'status', 'is_active')
	search_fields = ('registration_number', 'vehicle_type')
	list_filter = ('status',)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
	list_display = ('name', 'phone', 'user', 'license_number', 'is_active')
	search_fields = ('name', 'phone', 'user__username', 'user__first_name', 'user__last_name', 'license_number')
	list_filter = ('is_active',)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
	list_display = ('order', 'driver', 'vehicle', 'destination', 'status', 'scheduled_date')
	search_fields = ('order__order_reference', 'driver__name', 'driver__license_number', 'vehicle__registration_number', 'destination')
	list_filter = ('status', 'scheduled_date')
	list_select_related = ('order', 'driver', 'vehicle')
