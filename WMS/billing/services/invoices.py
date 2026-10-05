from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from deliveries.models import Delivery
from orders.models import Order

from billing.models import Invoice, InvoiceItem


@transaction.atomic
def generate_invoice(order, due_date, acting_user):
	if not (acting_user.is_superuser or acting_user.role in {User.Role.ADMIN, User.Role.ACCOUNTS}):
		raise PermissionDenied('Only administrators and accounts staff can issue invoices.')

	order = Order.objects.select_for_update().select_related('client').get(pk=order.pk)
	if order.status != 'delivered' or not order.deliveries.filter(status=Delivery.Status.DELIVERED).exists():
		raise ValidationError('An invoice can only be generated for a delivered order.')
	if Invoice.objects.filter(order=order).exists():
		raise ValidationError('This order already has an invoice.')
	if due_date is None:
		raise ValidationError({'due_date': 'A due date is required.'})

	items = list(order.items.select_related('product').all())
	if not items:
		raise ValidationError('An invoice cannot be generated for an order without items.')
	total = sum((item.subtotal for item in items), Decimal('0.00'))
	year = timezone.localdate().year
	invoice = Invoice.objects.create(
		order=order,
		client=order.client,
		invoice_number=f'PENDING-{uuid4().hex}',
		issue_date=timezone.localdate(),
		due_date=due_date,
		subtotal=total,
		total=total,
		total_amount=total,
		outstanding_balance=total,
		payment_status=Invoice.PaymentStatus.UNPAID,
		status='issued',
	)
	invoice.invoice_number = f'INV-{year}-{invoice.pk:04d}'
	invoice.save(update_fields=['invoice_number'])
	InvoiceItem.objects.bulk_create([
		InvoiceItem(
			invoice=invoice,
			product=item.product,
			product_name=item.product.name,
			product_sku=item.product.sku,
			quantity=item.quantity,
			unit_price=item.unit_price,
			subtotal=item.subtotal,
		)
		for item in items
	])
	return invoice