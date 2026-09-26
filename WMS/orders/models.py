from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Order(models.Model):
	STATUS_CHOICES = [
		('pending', 'Pending'),
		('confirmed', 'Confirmed'),
		('preparing', 'Preparing'),
		('dispatched', 'Dispatched'),
		('delivered', 'Delivered'),
		('cancelled', 'Cancelled'),
		('partially_delivered', 'Partially Delivered'),
	]

	order_reference = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
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

	def save(self, *args, **kwargs):
		if self.pk is None:
			super().save(*args, **kwargs)
		if not self.order_reference:
			self.order_reference = f'ORD-{self.pk:05d}'
			super().save(update_fields=['order_reference'])
		elif kwargs.get('update_fields') is not None:
			kwargs['update_fields'] = set(kwargs['update_fields']) | {'updated_at'}
			super().save(*args, **kwargs)
		else:
			super().save(*args, **kwargs)

	def recalculate_total(self):
		total = self.items.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
		Order.objects.filter(pk=self.pk).update(total_amount=total, updated_at=timezone.now())
		self.total_amount = total

	def __str__(self):
		return f'{self.order_reference or "New order"} - {self.client}'


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='order_items')
	quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
	unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
	subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)

	def clean(self):
		super().clean()
		if self.quantity is not None and self.quantity <= 0:
			raise ValidationError({'quantity': 'Quantity must be greater than zero.'})
		if self.unit_price is not None and self.unit_price < 0:
			raise ValidationError({'unit_price': 'Price cannot be negative.'})

	def save(self, *args, **kwargs):
		previous_product_id = None
		if self.pk is not None:
			previous_product_id = type(self).objects.filter(pk=self.pk).values_list('product_id', flat=True).first()
		if previous_product_id != self.product_id:
			self.unit_price = self.product.unit_price
		self.full_clean()
		self.subtotal = self.quantity * self.unit_price
		if kwargs.get('update_fields') is not None:
			kwargs['update_fields'] = set(kwargs['update_fields']) | {'subtotal'}
		super().save(*args, **kwargs)
		self.order.recalculate_total()

	def delete(self, *args, **kwargs):
		order = self.order
		result = super().delete(*args, **kwargs)
		order.recalculate_total()
		return result

	@property
	def line_total(self):
		return self.subtotal

	def __str__(self):
		return f'{self.order} - {self.product.name}'
