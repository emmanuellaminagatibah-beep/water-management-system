from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import User

from billing.models import Invoice, Payment


@transaction.atomic
def record_payment(invoice, amount, method, reference, acting_user):
	if not (acting_user.is_superuser or acting_user.role in {User.Role.ADMIN, User.Role.ACCOUNTS}):
		raise PermissionDenied('Only administrators and accounts staff can record payments.')

	try:
		amount = Decimal(str(amount))
	except (InvalidOperation, TypeError, ValueError):
		raise ValidationError('Enter a valid payment amount.')
	if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
		raise ValidationError('Payment amount must be greater than zero with at most two decimal places.')
	if method not in Payment.Method.values:
		raise ValidationError({'method': 'Choose a valid payment method.'})

	locked_invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
	if locked_invoice.status == 'cancelled':
		raise ValidationError('Payments cannot be recorded against a cancelled invoice.')
	total = locked_invoice.total_amount or locked_invoice.total
	paid = locked_invoice.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	outstanding = max(total - paid, Decimal('0.00'))
	if amount > outstanding:
		raise ValidationError('Payment cannot exceed the outstanding invoice balance.')

	payment = Payment.objects.create(
		invoice=locked_invoice,
		amount=amount,
		method=method,
		reference=(reference or '').strip(),
		payment_date=timezone.localdate(),
		received_by=acting_user,
	)
	paid += amount
	locked_invoice.outstanding_balance = max(total - paid, Decimal('0.00'))
	if locked_invoice.outstanding_balance == 0:
		locked_invoice.payment_status = Invoice.PaymentStatus.FULLY_PAID
		locked_invoice.status = 'paid'
	elif paid > 0:
		locked_invoice.payment_status = Invoice.PaymentStatus.PARTIALLY_PAID
		locked_invoice.status = 'part_paid'
	else:
		locked_invoice.payment_status = Invoice.PaymentStatus.UNPAID
		locked_invoice.status = 'issued'
	locked_invoice.save(update_fields=['outstanding_balance', 'payment_status', 'status'])
	return payment