from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from billing.models import Invoice, Payment
from billing.services.invoices import generate_invoice
from billing.services.payments import record_payment
from clients.models import Client
from complaints.models import Complaint
from deliveries.models import Delivery, Driver, Vehicle
from deliveries.services import change_delivery_status, schedule_delivery
from Inventory.models import Inventory, StockMovement
from Inventory.services import adjust_stock
from orders.models import Order, OrderItem
from orders.services import confirm_order, prepare_order
from products.models import Product

from accounts.models import User


class Command(BaseCommand):
	help = 'Safely create or advance a complete AquaFlow demonstration workflow.'

	@transaction.atomic
	def handle(self, *args, **options):
		if not settings.DEBUG:
			raise CommandError('Demo accounts can only be created while DJANGO_DEBUG is enabled.')

		admin = self._ensure_user('demo_admin', User.Role.ADMIN, is_staff=True, is_superuser=True)
		sales = self._ensure_user('demo_sales', User.Role.SALES)
		warehouse = self._ensure_user('demo_warehouse', User.Role.WAREHOUSE)
		driver_user = self._ensure_user('demo_driver', User.Role.DRIVER)
		accounts = self._ensure_user('demo_accounts', User.Role.ACCOUNTS)
		client_user = self._ensure_user('demo_client', User.Role.CLIENT)

		client, _ = Client.objects.get_or_create(
			user=client_user,
			defaults={
				'client_id': 'DEMO-CLIENT-001',
				'business_name': 'AquaFlow Demo Customer',
				'phone': '0240000100',
				'email': 'demo-client@example.test',
				'address': 'Accra, Ghana',
				'category': 'business',
			},
		)
		product, _ = Product.objects.get_or_create(
			sku='DEMO-WATER-20L',
			defaults={
				'name': 'Demo Spring Water 20L',
				'category': 'bottled',
				'package_size': '20l',
				'unit_price': Decimal('15.00'),
				'reorder_level': 10,
			},
		)
		inventory, inventory_created = Inventory.objects.get_or_create(
			product=product,
			defaults={'quantity': 0, 'reorder_level': 10},
		)
		if inventory_created:
			adjust_stock(
				product, 50, StockMovement.MovementType.OPENING, user=warehouse,
				note='Demo opening balance', reference='DEMO-OPENING',
			)
		else:
			inventory.refresh_from_db()
			if inventory.available_quantity < 2:
				adjust_stock(
					product, 2 - inventory.available_quantity, StockMovement.MovementType.RECEIVED,
					user=warehouse, note='Demo replenishment', reference='DEMO-RESTOCK',
				)

		order, _ = Order.objects.get_or_create(
			client=client,
			notes='DEMO-FLOW-001',
			defaults={'created_by': client_user},
		)
		if not order.items.exists():
			OrderItem.objects.create(order=order, product=product, quantity=2)
		if order.status == 'pending':
			confirm_order(order, user=sales)
		order.refresh_from_db()
		if order.status == 'confirmed':
			prepare_order(order, acting_user=warehouse)
		order.refresh_from_db()

		driver, _ = Driver.objects.get_or_create(
			user=driver_user,
			defaults={'name': 'Demo Driver', 'phone': driver_user.phone, 'license_number': 'DEMO-LIC-001'},
		)
		vehicle, _ = Vehicle.objects.get_or_create(
			registration_number='DEMO-TRUCK-001',
			defaults={'vehicle_type': 'Delivery truck', 'capacity_litres': 5000},
		)
		delivery = order.deliveries.order_by('pk').first()
		if delivery is None:
			if order.status not in {'confirmed', 'preparing'}:
				raise CommandError('The demo order cannot be scheduled in its current status.')
			delivery = schedule_delivery(
				order=order,
				driver=driver,
				vehicle=vehicle,
				destination=client.address,
				scheduled_date=timezone.now() + timedelta(days=1),
			)
		if delivery.status == Delivery.Status.SCHEDULED:
			change_delivery_status(
				delivery=delivery,
				new_status=Delivery.Status.DISPATCHED,
				acting_user=sales,
				status_note='Demo dispatch',
			)
		delivery.refresh_from_db()
		if delivery.status == Delivery.Status.DISPATCHED:
			change_delivery_status(
				delivery=delivery,
				new_status=Delivery.Status.DELIVERED,
				acting_user=driver_user,
				status_note='Demo delivery completed',
			)
		delivery.refresh_from_db()
		order.refresh_from_db()

		invoice = Invoice.objects.filter(order=order).first()
		if invoice is None:
			invoice = generate_invoice(order, timezone.localdate() + timedelta(days=30), accounts)
		if not invoice.payments.filter(reference='DEMO-RECEIPT-001').exists() and invoice.outstanding_balance > 0:
			record_payment(
				invoice=invoice,
				amount=min(invoice.outstanding_balance, Decimal('10.00')),
				method=Payment.Method.MOBILE_MONEY,
				reference='DEMO-RECEIPT-001',
				acting_user=accounts,
			)
		Complaint.objects.get_or_create(
			client=client,
			title='Demo delivery feedback',
			defaults={'order': order, 'description': 'Demonstration customer support request.'},
		)

		self.stdout.write(self.style.SUCCESS(
			f'Demo flow ready: {client.client_id}, {order.order_reference}, '
			f'{delivery.get_status_display()}, {invoice.invoice_number}. '
			f'Admin dashboard: /dashboards/admin/.'
		))

	def _ensure_user(self, username, role, *, is_staff=False, is_superuser=False):
		user, created = User.objects.get_or_create(
			username=username,
			defaults={
				'email': f'{username}@example.test',
				'role': role,
				'is_staff': is_staff,
				'is_superuser': is_superuser,
			},
		)
		changed = []
		if user.role != role:
			user.role = role
			changed.append('role')
		if user.is_staff != is_staff:
			user.is_staff = is_staff
			changed.append('is_staff')
		if user.is_superuser != is_superuser:
			user.is_superuser = is_superuser
			changed.append('is_superuser')
		if created:
			user.set_password('DemoWater2026!')
			changed.append('password')
		if changed:
			user.save(update_fields=changed)
		return user