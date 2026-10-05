from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from clients.models import Client
from deliveries.models import Delivery, Driver, Vehicle
from orders.models import Order
from orders.models import OrderItem
from products.models import Product

from .models import Invoice, Payment
from .services.invoices import generate_invoice
from .services.payments import record_payment


class BillingWorkflowTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.accounts_user = get_user_model().objects.create_user(username='billing-user', role='accounts')
		cls.client_record = Client.objects.create(
			client_id='BILL001', business_name='Billing Customer', phone='0241000000', address='Accra',
		)
		cls.order = Order.objects.create(
			client=cls.client_record,
			status='confirmed',
			total_amount=Decimal('100.00'),
		)
		cls.invoice = Invoice.objects.create(
			order=cls.order,
			invoice_number='INV-BILL-001',
			subtotal=Decimal('100.00'),
			total=Decimal('100.00'),
		)

	def setUp(self):
		self.client.force_login(self.accounts_user)

	def test_accounts_user_can_issue_invoice_for_eligible_order(self):
		order, product = self.create_delivered_order('50.00')

		response = self.client.post(reverse('invoice_create'), {
			'order': order.pk,
			'due_date': (date.today() + timedelta(days=14)).isoformat(),
		})

		invoice = Invoice.objects.get(order=order)
		self.assertRedirects(response, reverse('invoice_detail', args=[invoice.pk]))
		self.assertEqual(invoice.total_amount, Decimal('50.00'))
		self.assertEqual(invoice.outstanding_balance, Decimal('50.00'))
		self.assertEqual(invoice.payment_status, Invoice.PaymentStatus.UNPAID)
		self.assertTrue(invoice.invoice_number.startswith(f'INV-{date.today().year}-'))
		self.assertEqual(invoice.items.get().product, product)

	def test_invoice_generation_rejects_duplicate_orders(self):
		order, _ = self.create_delivered_order('35.00')
		generate_invoice(order, date.today() + timedelta(days=7), self.accounts_user)

		with self.assertRaises(ValidationError):
			generate_invoice(order, date.today() + timedelta(days=7), self.accounts_user)

	def test_invoice_item_values_are_snapshots(self):
		order, product = self.create_delivered_order('24.00')
		invoice = generate_invoice(order, date.today() + timedelta(days=7), self.accounts_user)
		product.name = 'Renamed product'
		product.unit_price = Decimal('99.00')
		product.save()
		invoice_item = invoice.items.get()

		self.assertEqual(invoice_item.product_name, 'Snapshot product')
		self.assertEqual(invoice_item.unit_price, Decimal('12.00'))
		self.assertEqual(invoice_item.subtotal, Decimal('24.00'))

	def test_unauthorised_user_cannot_generate_invoice(self):
		client_user = get_user_model().objects.create_user(username='invoice-client', role='client')
		order, _ = self.create_delivered_order('20.00')

		with self.assertRaises(PermissionDenied):
			generate_invoice(order, date.today() + timedelta(days=7), client_user)

		self.client.force_login(client_user)
		self.assertEqual(self.client.post(reverse('invoice_create')).status_code, 403)

	def test_payment_updates_invoice_balance_status(self):
		response = self.client.post(reverse('payment_create', args=[self.invoice.pk]), {
			'amount': '40.00', 'method': 'cash', 'reference': 'RCPT-001',
		})
		self.assertRedirects(response, reverse('payment_history', args=[self.invoice.pk]))
		self.invoice.refresh_from_db()
		self.assertEqual(self.invoice.status, 'part_paid')
		self.assertEqual(self.invoice.payment_status, Invoice.PaymentStatus.PARTIALLY_PAID)
		self.assertEqual(self.invoice.outstanding_balance, Decimal('60.00'))
		self.assertEqual(Payment.objects.count(), 1)
		self.assertEqual(Payment.objects.get().received_by, self.accounts_user)

		self.client.post(reverse('payment_create', args=[self.invoice.pk]), {
			'amount': '60.00', 'method': 'bank_transfer', 'reference': 'RCPT-002',
		})
		self.invoice.refresh_from_db()
		self.assertEqual(self.invoice.status, 'paid')
		self.assertEqual(self.invoice.payment_status, Invoice.PaymentStatus.FULLY_PAID)
		self.assertEqual(self.invoice.outstanding_balance, Decimal('0.00'))

	def test_payment_cannot_exceed_outstanding_balance(self):
		self.client.post(reverse('payment_create', args=[self.invoice.pk]), {
			'amount': '101.00', 'method': 'cash', 'reference': '',
		})
		self.assertFalse(Payment.objects.exists())
		self.invoice.refresh_from_db()
		self.assertEqual(self.invoice.status, 'issued')

	def test_payment_service_rejects_zero_and_negative_amounts(self):
		for amount in ('0.00', '-1.00'):
			with self.subTest(amount=amount), self.assertRaises(ValidationError):
				record_payment(self.invoice, amount, Payment.Method.CASH, '', self.accounts_user)

	def test_unauthorised_user_cannot_record_payment(self):
		client_user = get_user_model().objects.create_user(username='payment-client', role='client')
		with self.assertRaises(PermissionDenied):
			record_payment(self.invoice, '10.00', Payment.Method.CASH, '', client_user)
		self.client.force_login(client_user)
		self.assertEqual(self.client.post(reverse('payment_create', args=[self.invoice.pk])).status_code, 403)

	def test_client_gets_404_for_another_clients_invoice(self):
		client_user = get_user_model().objects.create_user(username='invoice-owner', role='client')
		own_client = Client.objects.create(
			user=client_user,
			client_id='BILL-OWNER',
			business_name='Invoice owner',
			phone='0241000002',
			address='Accra',
		)
		other_order = Order.objects.create(client=self.client_record, status='delivered')
		other_invoice = Invoice.objects.create(
			order=other_order,
			client=self.client_record,
			invoice_number='INV-PRIVATE-001',
			total_amount=Decimal('15.00'),
		)
		self.assertNotEqual(own_client, other_invoice.client)
		self.client.force_login(client_user)

		response = self.client.get(reverse('invoice_detail', args=[other_invoice.pk]))

		self.assertEqual(response.status_code, 404)

	def create_delivered_order(self, unit_price):
		product = Product.objects.create(
			sku=f'SNAP-{Order.objects.count():03d}',
			name='Snapshot product',
			unit_price=Decimal(unit_price) / 2,
		)
		order = Order.objects.create(client=self.client_record, status='delivered')
		OrderItem.objects.create(order=order, product=product, quantity=2)
		vehicle = Vehicle.objects.create(registration_number=f'INV-{Order.objects.count():03d}')
		driver = Driver.objects.create(license_number=f'INV-LIC-{Order.objects.count():03d}')
		Delivery.objects.create(order=order, vehicle=vehicle, driver=driver, status=Delivery.Status.DELIVERED)
		return order, product
