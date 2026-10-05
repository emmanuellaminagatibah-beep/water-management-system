from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Invoice(models.Model):
	class PaymentStatus(models.TextChoices):
		UNPAID = 'UNPAID', 'Unpaid'
		PARTIALLY_PAID = 'PARTIALLY_PAID', 'Partially paid'
		FULLY_PAID = 'FULLY_PAID', 'Fully paid'

	STATUS_CHOICES = [
		('issued', 'Issued'),
		('part_paid', 'Part paid'),
		('paid', 'Paid'),
		('overdue', 'Overdue'),
		('cancelled', 'Cancelled'),
	]

	order = models.OneToOneField('orders.Order', on_delete=models.PROTECT, related_name='invoice')
	client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='invoices', null=True, blank=True)
	invoice_number = models.CharField(max_length=40, unique=True)
	issue_date = models.DateField(default=timezone.localdate)
	total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
	subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='issued')
	due_date = models.DateField(null=True, blank=True)
	issued_at = models.DateTimeField(auto_now_add=True)

	def save(self, *args, **kwargs):
		if self.order_id and not self.client_id:
			self.client = self.order.client
		super().save(*args, **kwargs)

	def __str__(self):
		return self.invoice_number


class InvoiceItem(models.Model):
	invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='invoice_items')
	product_name = models.CharField(max_length=150)
	product_sku = models.CharField(max_length=40)
	quantity = models.PositiveIntegerField()
	unit_price = models.DecimalField(max_digits=10, decimal_places=2)
	subtotal = models.DecimalField(max_digits=12, decimal_places=2)

	def __str__(self):
		return f'{self.invoice.invoice_number} - {self.product_name}'


class Payment(models.Model):
	class Method(models.TextChoices):
		CASH = 'cash', 'Cash'
		BANK_TRANSFER = 'bank_transfer', 'Bank transfer'
		MOBILE_MONEY = 'mobile_money', 'Mobile money'
		CARD = 'card', 'Card'

	METHOD_CHOICES = Method.choices

	invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	method = models.CharField(max_length=20, choices=METHOD_CHOICES)
	reference = models.CharField(max_length=100, blank=True)
	payment_date = models.DateField(default=timezone.localdate)
	paid_at = models.DateTimeField(auto_now_add=True)
	received_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='received_payments',
	)

	class Meta:
		constraints = [
			models.CheckConstraint(condition=Q(amount__gt=0), name='payment_amount_positive'),
		]

	def __str__(self):
		return f'{self.invoice.invoice_number} - {self.amount}'
