from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def normalize_delivery_status(value):
	if value is None:
		return None
	value = str(value).strip()
	if not value:
		return value
	mapping = {
		'scheduled': 'SCHEDULED',
		'in_transit': 'DISPATCHED',
		'dispatched': 'DISPATCHED',
		'delivered': 'DELIVERED',
		'partially_delivered': 'PARTIALLY_DELIVERED',
		'failed': 'FAILED',
		'cancelled': 'CANCELLED',
	}
	return mapping.get(value.lower(), value.upper())


class Vehicle(models.Model):
	class Status(models.TextChoices):
		ACTIVE = 'active', 'Active'
		INACTIVE = 'inactive', 'Inactive'
		MAINTENANCE = 'maintenance', 'Maintenance'

	registration_number = models.CharField(max_length=30, unique=True)
	vehicle_type = models.CharField(max_length=50, blank=True)
	capacity_litres = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)
	status = models.CharField(
		max_length=20,
		choices=Status.choices,
		default=Status.ACTIVE,
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
	class Status(models.TextChoices):
		SCHEDULED = 'SCHEDULED', 'Scheduled'
		DISPATCHED = 'DISPATCHED', 'Dispatched'
		DELIVERED = 'DELIVERED', 'Delivered'
		PARTIALLY_DELIVERED = 'PARTIALLY_DELIVERED', 'Partially delivered'
		FAILED = 'FAILED', 'Failed'
		CANCELLED = 'CANCELLED', 'Cancelled'

	STATUS_CHOICES = Status.choices

	order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, related_name='deliveries')
	vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='deliveries')
	driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name='deliveries')
	destination = models.TextField(blank=True)
	status = models.CharField(max_length=30, choices=Status.choices, default=Status.SCHEDULED)
	scheduled_date = models.DateTimeField(null=True, blank=True)
	dispatched_at = models.DateTimeField(null=True, blank=True)
	completed_at = models.DateTimeField(null=True, blank=True)
	status_note = models.TextField(blank=True)
	delivered_at = models.DateTimeField(null=True, blank=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

	def clean(self):
		super().clean()
		errors = {}
		self.status = normalize_delivery_status(self.status)
		if self.driver_id and not self.driver.is_active:
			errors['driver'] = 'Select an active driver.'
		if self.vehicle_id and (self.vehicle.status != Vehicle.Status.ACTIVE or not self.vehicle.is_active):
			errors['vehicle'] = 'Select a vehicle with Active status.'
		if self.order_id and self.order.status not in {'confirmed', 'preparing'}:
			errors['order'] = 'Only confirmed or preparing orders can be scheduled for delivery.'
		if errors:
			raise ValidationError(errors)

	def save(self, *args, **kwargs):
		if self.status:
			self.status = normalize_delivery_status(self.status)
		super().save(*args, **kwargs)

	def __str__(self):
		return f'Delivery for {self.order}'
