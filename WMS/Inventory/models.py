from django.conf import settings
from django.db import models


class InventoryQuerySet(models.QuerySet):
	def low_stock(self):
		return self.filter(quantity__lte=models.F('reorder_level'))


class Inventory(models.Model):
	objects = InventoryQuerySet.as_manager()

	product = models.OneToOneField('products.Product', on_delete=models.CASCADE, related_name='inventory')
	quantity = models.PositiveIntegerField(default=0)
	reorder_level = models.PositiveIntegerField(default=0)
	reserved_quantity = models.PositiveIntegerField(default=0)
	location = models.CharField(max_length=100, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	@property
	def quantity_on_hand(self):
		return self.quantity

	@property
	def is_low_stock(self):
		return self.quantity <= self.reorder_level

	@property
	def available_quantity(self):
		return self.quantity - self.reserved_quantity

	def __str__(self):
		return f'{self.product.name}: {self.quantity}'


class StockMovement(models.Model):
	class MovementType(models.TextChoices):
		OPENING = 'opening', 'Opening Stock'
		RECEIVED = 'in', 'Stock Received'
		ISSUED = 'out', 'Stock Issued'
		DAMAGED = 'damaged', 'Damaged'
		RETURNED = 'returned', 'Returned'
		ADJUSTMENT = 'adjustment', 'Adjustment'

	MOVEMENT_TYPES = MovementType.choices

	product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='stock_movements')
	movement_type = models.CharField(max_length=12, choices=MOVEMENT_TYPES)
	quantity = models.PositiveIntegerField()
	reference = models.CharField(max_length=120, blank=True)
	note = models.CharField(max_length=255, blank=True)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='stock_movements',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.product.sku} - {self.movement_type} ({self.quantity})'
