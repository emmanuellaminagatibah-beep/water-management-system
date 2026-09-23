from decimal import Decimal

from django.conf import settings
from django.db import models


class Order(models.Model):
	STATUS_CHOICES = [
		('pending', 'Pending'),
		('confirmed', 'Confirmed'),
		('processing', 'Processing'),
		('delivered', 'Delivered'),
		('cancelled', 'Cancelled'),
	]

	client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='orders')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
	total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	notes = models.TextField(blank=True)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='created_orders',
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'Order #{self.pk} - {self.client.name}'


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='order_items')
	quantity = models.PositiveIntegerField()
	unit_price = models.DecimalField(max_digits=10, decimal_places=2)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['order', 'product'], name='unique_product_per_order'),
		]

	@property
	def line_total(self):
		return self.quantity * self.unit_price

	def __str__(self):
		return f'{self.order} - {self.product.name}'
