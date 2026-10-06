from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from billing.models import Invoice, Payment
from clients.models import Client
from complaints.models import Complaint
from deliveries.models import Delivery, Driver, Vehicle
from Inventory.models import Inventory
from orders.models import Order, OrderItem
from products.models import Product


class RoleDashboardTests(TestCase):
	def test_public_homepage_has_sign_in_about_and_contact(self):
		response = self.client.get(reverse('home'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, f'href="{reverse("login")}"')
		self.assertContains(response, 'About Agatibahsprings')
		self.assertContains(response, 'id="contact"')
		self.assertContains(response, 'Sign in to contact your service team')

	def test_each_role_sees_its_own_workspace(self):
		dashboards = {
			'admin': ('Operations', '/admin/accounts/user/', '🛡️'),
			'sales': ('Sales', '/orders/create/', '🧾'),
			'warehouse': ('Warehouse', '/Inventory/movements/', '📦'),
			'driver': ('Field Operations', '/deliveries/', '🚚'),
			'accounts': ('Finance', '/billing/', '💳'),
			'client': ('Customer', '/orders/my/', '🛒'),
		}

		for role, (title, action_url, emoji) in dashboards.items():
			with self.subTest(role=role):
				user = get_user_model().objects.create_user(
					username=f'dashboard-{role}',
					role=role,
				)
				self.client.force_login(user)
				response = self.client.get(reverse('dashboard'))

				self.assertEqual(response.status_code, 200)
				self.assertContains(response, '/static/dashboards/js/site.js')
				if role == 'admin':
					self.assertContains(response, 'Operations at a glance')
					self.assertContains(response, 'Total clients')
				elif role == 'client':
					self.assertContains(response, 'My service')
					self.assertContains(response, 'Outstanding invoices')
				else:
					self.assertContains(response, f'{title} dashboard')
					self.assertEqual(len(response.context['dashboard_metrics']), 3)
					self.assertContains(response, f'href="{action_url}"')
					self.assertContains(response, '<details class="action">')
					self.assertContains(response, emoji)
					self.assertContains(response, 'Open workspace')

	def test_client_dashboard_only_shows_the_owning_clients_records(self):
		user = get_user_model().objects.create_user(username='portal-owner', role='client')
		own_client = Client.objects.create(
			user=user, client_id='PORTAL001', business_name='Own Customer', phone='0243000000', address='Accra',
		)
		other_client = Client.objects.create(
			client_id='PORTAL002', business_name='Private Customer', phone='0243000001', address='Tema',
		)
		own_product = Product.objects.create(sku='PORTAL-OWN', name='Own product')
		other_product = Product.objects.create(sku='PORTAL-OTHER', name='Private product')
		own_order = Order.objects.create(client=own_client, status='pending')
		other_order = Order.objects.create(client=other_client, status='pending')
		OrderItem.objects.create(order=own_order, product=own_product, quantity=1)
		OrderItem.objects.create(order=other_order, product=other_product, quantity=1)
		vehicle = Vehicle.objects.create(registration_number='PORTAL-TRUCK')
		driver = Driver.objects.create(license_number='PORTAL-LIC')
		Delivery.objects.create(order=own_order, vehicle=vehicle, driver=driver)
		Delivery.objects.create(order=other_order, vehicle=vehicle, driver=driver)
		own_invoice = Invoice.objects.create(
			order=own_order, client=own_client, invoice_number='INV-PORTAL-OWN', total_amount=10, outstanding_balance=7,
		)
		other_invoice = Invoice.objects.create(
			order=other_order, client=other_client, invoice_number='INV-PORTAL-OTHER', total_amount=20, outstanding_balance=20,
		)
		Payment.objects.create(invoice=own_invoice, amount=3, method=Payment.Method.CASH)
		Payment.objects.create(invoice=other_invoice, amount=4, method=Payment.Method.CASH)
		Complaint.objects.create(client=own_client, title='Own complaint', description='My issue')
		Complaint.objects.create(client=other_client, title='Private complaint', description='Other issue')
		self.client.force_login(user)

		response = self.client.get(reverse('dashboard'))

		self.assertEqual(response.status_code, 200)
		for visible_value in ('Own product', own_order.order_reference, 'INV-PORTAL-OWN', 'Own complaint'):
			self.assertContains(response, visible_value)
		for private_value in ('Private product', other_order.order_reference, 'INV-PORTAL-OTHER', 'Private complaint'):
			self.assertNotContains(response, private_value)
		self.assertEqual(response.context['outstanding_balance'], 7)


class AdminDashboardTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.admin = get_user_model().objects.create_user(username='reports-admin', role='admin')
		cls.client_record = Client.objects.create(
			client_id='REPORT001', business_name='Report customer', phone='0244000000', address='Accra',
		)
		product = Product.objects.create(sku='REPORT-WATER', name='Report water')
		Inventory.objects.create(product=product, quantity=3, reorder_level=5)
		order = Order.objects.create(client=cls.client_record, status='pending')
		OrderItem.objects.create(order=order, product=product, quantity=2)
		vehicle = Vehicle.objects.create(registration_number='REPORT-TRUCK')
		driver = Driver.objects.create(license_number='REPORT-LIC')
		Delivery.objects.create(order=order, vehicle=vehicle, driver=driver)
		invoice = Invoice.objects.create(
			order=order,
			client=cls.client_record,
			invoice_number='INV-REPORT-001',
			total_amount=100,
			outstanding_balance=40,
		)
		Payment.objects.create(invoice=invoice, amount=60, method=Payment.Method.CASH, received_by=cls.admin)
		Complaint.objects.create(client=cls.client_record, title='Report issue', description='Open issue')

	def test_admin_dashboard_uses_real_database_totals(self):
		self.client.force_login(self.admin)
		response = self.client.get(reverse('admin_dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['total_clients'], 1)
		self.assertEqual(response.context['pending_orders'], 1)
		self.assertEqual(response.context['deliveries_awaiting'], 1)
		self.assertEqual(response.context['available_products'], 1)
		self.assertEqual(response.context['low_stock_products'], 1)
		self.assertEqual(response.context['outstanding_total'], 40)
		self.assertEqual(response.context['open_complaints'], 1)
		self.assertEqual(len(response.context['recent_payments']), 1)

	def test_reports_support_date_filters(self):
		self.client.force_login(self.admin)
		response = self.client.get(reverse('report_list', args=['sales']), {'end_date': '2000-01-01'})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(list(response.context['rows']), [])

	def test_dashboard_and_reports_forbid_non_admin_users(self):
		user = get_user_model().objects.create_user(username='reports-sales', role='sales')
		self.client.force_login(user)
		self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 403)
		for report_type in ('sales', 'inventory', 'orders', 'deliveries', 'payments'):
			with self.subTest(report=report_type):
				self.assertEqual(self.client.get(reverse('report_list', args=[report_type])).status_code, 403)


class ErrorPageTests(TestCase):
	def test_friendly_error_views_return_expected_status_codes(self):
		from .views import page_not_found, permission_denied, server_error

		request = RequestFactory().get('/')
		for view, expected_status in (
			(permission_denied, 403),
			(page_not_found, 404),
			(server_error, 500),
		):
			with self.subTest(status=expected_status):
				response = view(request)
				self.assertEqual(response.status_code, expected_status)
