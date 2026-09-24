from decimal import Decimal

from django.db import models


class Product(models.Model):
	CATEGORY_CHOICES = [
		('sachet', 'Sachet Water'),
		('bottled', 'Bottled Water'),
		('dispenser', 'Dispenser Water'),
		('other', 'Other'),
	]

	PACKAGE_SIZE_CHOICES = [
		('500ml', '500 ml'),
		('1.5l', '1.5 litres'),
		('5l', '5 litres'),
		('10l', '10 litres'),
		('20l', '20 litres'),
	]

	sku = models.CharField(max_length=40, unique=True)
	name = models.CharField(max_length=150)
	category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='bottled')
	package_size = models.CharField(max_length=10, choices=PACKAGE_SIZE_CHOICES, default='500ml')
	unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	reorder_level = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return f'{self.sku} - {self.name}'
