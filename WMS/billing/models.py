from decimal import Decimal

from django.db import models


class Invoice(models.Model):
	STATUS_CHOICES = [
		('issued', 'Issued'),
		('part_paid', 'Part paid'),
		('paid', 'Paid'),
		('overdue', 'Overdue'),
		('cancelled', 'Cancelled'),
	]

	order = models.OneToOneField('orders.Order', on_delete=models.PROTECT, related_name='invoice')
	invoice_number = models.CharField(max_length=40, unique=True)
	subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='issued')
	due_date = models.DateField(null=True, blank=True)
	issued_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.invoice_number


class Payment(models.Model):
	METHOD_CHOICES = [
		('cash', 'Cash'),
		('bank', 'Bank transfer'),
		('card', 'Card'),
		('mobile', 'Mobile money'),
	]

	invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	method = models.CharField(max_length=20, choices=METHOD_CHOICES)
	reference = models.CharField(max_length=100, blank=True)
	paid_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f'{self.invoice.invoice_number} - {self.amount}'
