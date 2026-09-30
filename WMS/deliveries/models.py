from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Vehicle(models.Model):
	registration_number = models.CharField(max_length=30, unique=True)
	vehicle_type = models.CharField(max_length=50, blank=True)
	capacity_litres = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)
	status = models.CharField(
		max_length=20,
		choices=[('active', 'Active'), ('inactive', 'Inactive'), ('maintenance', 'Maintenance')],
		default='active',
	)
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

	def __str__(self):
		return self.registration_number


class Driver(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		related_name='driver_profile',
		null=True,
		blank=True,
	)
	name = models.CharField(max_length=150, blank=True)
	phone = models.CharField(max_length=20, blank=True)
	license_number = models.CharField(max_length=50, unique=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

	def __str__(self):
		return self.name or (self.user.get_full_name() or self.user.username if self.user else self.license_number)


class Delivery(models.Model):
	STATUS_CHOICES = [
		('scheduled', 'Scheduled'),
		('in_transit', 'In transit'),
		('delivered', 'Delivered'),
		('failed', 'Failed'),
	]

	order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, related_name='delivery')
	vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='deliveries')
	driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name='deliveries')
	destination = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
	scheduled_date = models.DateTimeField(null=True, blank=True)
	delivered_at = models.DateTimeField(null=True, blank=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

	def clean(self):
		super().clean()
		errors = {}
		if self.driver_id and not self.driver.is_active:
			errors['driver'] = 'Select an active driver.'
		if self.vehicle_id and (self.vehicle.status != 'active' or not self.vehicle.is_active):
			errors['vehicle'] = 'Select a vehicle with Active status.'
		if self.order_id and self.order.status not in {'confirmed', 'preparing'}:
			errors['order'] = 'Only confirmed or preparing orders can be scheduled for delivery.'
		if errors:
			raise ValidationError(errors)

	def __str__(self):
		return f'Delivery for {self.order}'
