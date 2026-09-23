from django.conf import settings
from django.db import models


class Vehicle(models.Model):
	registration_number = models.CharField(max_length=30, unique=True)
	capacity_litres = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return self.registration_number


class Driver(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='driver_profile')
	license_number = models.CharField(max_length=50, unique=True)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return self.user.get_full_name() or self.user.username


class Delivery(models.Model):
	STATUS_CHOICES = [
		('scheduled', 'Scheduled'),
		('in_transit', 'In transit'),
		('delivered', 'Delivered'),
		('failed', 'Failed'),
	]

	order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='delivery')
	vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
	driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
	scheduled_date = models.DateField(null=True, blank=True)
	delivered_at = models.DateTimeField(null=True, blank=True)
	notes = models.TextField(blank=True)

	def __str__(self):
		return f'Delivery for {self.order}'
