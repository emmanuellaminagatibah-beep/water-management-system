from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


def backfill_invoice_data(apps, schema_editor):
	Invoice = apps.get_model('billing', 'Invoice')
	InvoiceItem = apps.get_model('billing', 'InvoiceItem')
	Payment = apps.get_model('billing', 'Payment')
	using = schema_editor.connection.alias

	for invoice in Invoice.objects.using(using).select_related('order').iterator():
		paid = Payment.objects.using(using).filter(invoice_id=invoice.pk).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
		total = invoice.total or invoice.subtotal or invoice.order.total_amount
		balance = max(total - paid, Decimal('0.00'))
		invoice.client_id = invoice.order.client_id
		invoice.total_amount = total
		invoice.outstanding_balance = balance
		invoice.payment_status = 'FULLY_PAID' if balance == 0 else 'PARTIALLY_PAID' if paid else 'UNPAID'
		if invoice.issued_at:
			invoice.issue_date = invoice.issued_at.date()
		invoice.save(update_fields=[
			'client', 'issue_date', 'total_amount', 'outstanding_balance', 'payment_status',
		])

		if not InvoiceItem.objects.using(using).filter(invoice_id=invoice.pk).exists():
			items = invoice.order.items.select_related('product').all()
			InvoiceItem.objects.using(using).bulk_create([
				InvoiceItem(
					invoice_id=invoice.pk,
					product_id=item.product_id,
					product_name=item.product.name,
					product_sku=item.product.sku,
					quantity=item.quantity,
					unit_price=item.unit_price,
					subtotal=item.subtotal,
				)
				for item in items
			])


class Migration(migrations.Migration):

	dependencies = [
		('billing', '0002_invoice_client_invoice_issue_date_and_more'),
	]

	operations = [
		migrations.RunPython(backfill_invoice_data, migrations.RunPython.noop),
	]