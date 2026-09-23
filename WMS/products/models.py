from decimal import Decimal

from django.db import models


class Product(models.Model):
	sku = models.CharField(max_length=40, unique=True)
	name = models.CharField(max_length=150)
	category = models.CharField(max_length=80, blank=True)
	unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	reorder_level = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return f'{self.sku} - {self.name}'
