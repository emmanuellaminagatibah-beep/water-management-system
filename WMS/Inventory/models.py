from django.conf import settings
from django.db import models


class Inventory(models.Model):
	product = models.OneToOneField('products.Product', on_delete=models.CASCADE, related_name='inventory')
	quantity = models.PositiveIntegerField(default=0)
	reserved_quantity = models.PositiveIntegerField(default=0)
	location = models.CharField(max_length=100, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	@property
	def available_quantity(self):
		return self.quantity - self.reserved_quantity

	def __str__(self):
		return f'{self.product.name}: {self.quantity}'


class StockMovement(models.Model):
	MOVEMENT_TYPES = [
		('in', 'Stock in'),
		('out', 'Stock out'),
		('adjustment', 'Adjustment'),
	]

	product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='stock_movements')
	movement_type = models.CharField(max_length=12, choices=MOVEMENT_TYPES)
	quantity = models.PositiveIntegerField()
	reference = models.CharField(max_length=120, blank=True)
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
