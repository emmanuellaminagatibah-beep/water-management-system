from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from clients.models import Client
from products.models import Product
from Inventory.models import Inventory, StockMovement

from .models import Order, OrderItem
from .services import cancel_order, confirm_order, prepare_order


class OrderWorkflowTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.staff = get_user_model().objects.create_user(
			username='orders-staff',
			password='test-password',
			is_staff=True,
		)
		cls.customer = Client.objects.create(
			client_id='CL001',
			business_name='Clear Water Stores',
			phone='0240000000',
			address='Accra',
		)
		cls.products = [
			Product.objects.create(sku=f'WATER-{index}', name=f'Water {index}', unit_price=price)
			for index, price in enumerate(('20.00', '30.00', '40.00'), start=1)
		]

	def setUp(self):
		self.client.force_login(self.staff)

	def create_order(self, quantities=(2, 1, 3)):
		order = Order.objects.create(client=self.customer)
		for product, quantity in zip(self.products, quantities):
			if quantity <= 0:
				continue
			OrderItem.objects.create(
				order=order,
				product=product,
				quantity=quantity,
				unit_price=product.unit_price,
			)
		return order

	def test_one_product_calculates_reference_subtotal_and_total(self):
		order = Order.objects.create(client=self.customer)
		item = OrderItem.objects.create(
			order=order,
			product=self.products[0],
			quantity=5,
			unit_price=Decimal('999.00'),
		)

		order.refresh_from_db()
		self.assertTrue(order.order_reference.startswith('ORD-'))
		self.assertEqual(order.status, 'pending')
		self.assertEqual(item.unit_price, Decimal('20.00'))
		self.assertEqual(item.subtotal, Decimal('100.00'))
		self.assertEqual(order.total_amount, Decimal('100.00'))

	def test_multiple_products_share_order_and_sum_correctly(self):
		order = self.create_order()

		self.assertEqual(order.items.count(), 3)
		self.assertEqual(
			list(order.items.order_by('product__name').values_list('subtotal', flat=True)),
			[Decimal('40.00'), Decimal('30.00'), Decimal('120.00')],
		)
		self.assertEqual(order.total_amount, Decimal('190.00'))

	def test_create_view_sets_current_prices_and_pending_status(self):
		response = self.client.post(reverse('order_create'), {
			'client': self.customer.pk,
			'items-TOTAL_FORMS': '3',
			'items-INITIAL_FORMS': '0',
			'items-MIN_NUM_FORMS': '1',
			'items-MAX_NUM_FORMS': '1000',
			'items-0-product': self.products[0].pk,
			'items-0-quantity': '2',
			'items-1-product': self.products[1].pk,
			'items-1-quantity': '3',
			'items-2-product': self.products[2].pk,
			'items-2-quantity': '1',
		})

		self.assertEqual(response.status_code, 302)
		order = Order.objects.get()
		self.assertEqual(order.status, 'pending')
		self.assertEqual(order.total_amount, Decimal('170.00'))
		self.assertEqual(list(order.items.values_list('unit_price', flat=True)), [
			Decimal('20.00'), Decimal('30.00'), Decimal('40.00'),
		])

	def test_search_by_reference_and_client_details(self):
		order = self.create_order()

		for search_term in (order.order_reference, 'Clear Water Stores', 'CL001', '0240000000'):
			with self.subTest(search_term=search_term):
				response = self.client.get(reverse('orders'), {'q': search_term})
				self.assertContains(response, order.order_reference)

	def test_date_filter(self):
		order = self.create_order()

		response = self.client.get(reverse('orders'), {'created_on': timezone.localdate().isoformat()})

		self.assertContains(response, order.order_reference)

	def test_sales_role_can_open_order_list_and_create_order(self):
		sales_user = get_user_model().objects.create_user(username='sales-orders', role='sales')
		self.client.force_login(sales_user)

		self.assertEqual(self.client.get(reverse('orders')).status_code, 200)
		self.assertEqual(self.client.get(reverse('order_create')).status_code, 200)

	def test_warehouse_can_view_orders_but_cannot_create_them(self):
		warehouse_user = get_user_model().objects.create_user(username='warehouse-orders', role='warehouse')
		self.client.force_login(warehouse_user)

		self.assertEqual(self.client.get(reverse('orders')).status_code, 200)
		self.assertEqual(self.client.get(reverse('order_create')).status_code, 302)

	def test_client_order_history_only_shows_their_orders(self):
		client_user = get_user_model().objects.create_user(username='client-orders', role='client')
		self.customer.user = client_user
		self.customer.save()
		own_order = Order.objects.create(client=self.customer)
		other_client = Client.objects.create(
			client_id='CL002', business_name='Other Customer', phone='0240000001', address='Tema',
		)
		other_order = Order.objects.create(client=other_client)
		self.client.force_login(client_user)

		response = self.client.get(reverse('my_orders'))

		self.assertContains(response, own_order.order_reference)
		self.assertNotContains(response, other_order.order_reference)

	def test_client_can_place_order_for_their_linked_profile(self):
		client_user = get_user_model().objects.create_user(username='client-order-form', role='client')
		self.customer.user = client_user
		self.customer.save()
		self.client.force_login(client_user)

		form_response = self.client.get(reverse('client_order_create'))
		self.assertEqual(form_response.status_code, 200)
		self.assertContains(form_response, f'name="client" value="{self.customer.pk}"')
		self.assertNotContains(form_response, '<select name="client"')

		response = self.client.post(reverse('client_order_create'), {
			'client': self.customer.pk,
			'items-TOTAL_FORMS': '1',
			'items-INITIAL_FORMS': '0',
			'items-MIN_NUM_FORMS': '1',
			'items-MAX_NUM_FORMS': '1000',
			'items-0-product': self.products[0].pk,
			'items-0-quantity': '2',
		})

		self.assertRedirects(response, reverse('my_orders'))
		order = Order.objects.get(created_by=client_user)
		self.assertEqual(order.client, self.customer)

	def test_client_cannot_submit_an_order_for_another_client(self):
		client_user = get_user_model().objects.create_user(username='client-order-owner', role='client')
		self.customer.user = client_user
		self.customer.save()
		other_client = Client.objects.create(
			client_id='CL003', business_name='Not This User', phone='0240000003', address='Ho',
		)
		self.client.force_login(client_user)

		response = self.client.post(reverse('client_order_create'), {
			'client': other_client.pk,
			'items-TOTAL_FORMS': '1',
			'items-INITIAL_FORMS': '0',
			'items-MIN_NUM_FORMS': '1',
			'items-MAX_NUM_FORMS': '1000',
			'items-0-product': self.products[0].pk,
			'items-0-quantity': '1',
		})

		self.assertEqual(response.status_code, 200)
		self.assertFalse(Order.objects.filter(created_by=client_user).exists())

	def test_status_filter_and_all_supported_statuses(self):
		order = self.create_order()
		for status in ('confirmed', 'preparing', 'dispatched', 'delivered'):
			order.status = status
			order.save()
			response = self.client.get(reverse('orders'), {'status': status})
			self.assertContains(response, order.order_reference)

		for status in ('cancelled', 'partially_delivered'):
			order.status = status
			order.save()
			self.assertEqual(order.status, status)

	def test_edit_updates_items_and_recalculates_total(self):
		order = self.create_order((1, 1, 1))
		response = self.client.post(reverse('order_edit', args=[order.pk]), {
			'client': self.customer.pk,
			'items-TOTAL_FORMS': '3',
			'items-INITIAL_FORMS': '3',
			'items-MIN_NUM_FORMS': '1',
			'items-MAX_NUM_FORMS': '1000',
			'items-0-id': order.items.get(product=self.products[0]).pk,
			'items-0-product': self.products[0].pk,
			'items-0-quantity': '4',
			'items-1-id': order.items.get(product=self.products[1]).pk,
			'items-1-product': self.products[1].pk,
			'items-1-quantity': '1',
			'items-2-id': order.items.get(product=self.products[2]).pk,
			'items-2-product': self.products[2].pk,
			'items-2-quantity': '1',
		})

		self.assertEqual(response.status_code, 302)
		order.refresh_from_db()
		self.assertEqual(order.status, 'pending')
		self.assertEqual(order.total_amount, Decimal('150.00'))

	def test_changing_product_uses_new_current_price(self):
		order = self.create_order((1, 1, 1))
		item = order.items.get(product=self.products[0])
		response = self.client.post(reverse('order_edit', args=[order.pk]), {
			'client': self.customer.pk,
			'status': 'pending',
			'items-TOTAL_FORMS': '2',
			'items-INITIAL_FORMS': '1',
			'items-MIN_NUM_FORMS': '1',
			'items-MAX_NUM_FORMS': '1000',
			'items-0-id': item.pk,
			'items-0-product': self.products[1].pk,
			'items-0-quantity': '2',
		})

		self.assertEqual(response.status_code, 302)
		item.refresh_from_db()
		order.refresh_from_db()
		self.assertEqual(item.unit_price, Decimal('30.00'))
		self.assertEqual(item.subtotal, Decimal('60.00'))
		self.assertEqual(order.total_amount, Decimal('130.00'))

	def test_item_quantity_must_be_positive(self):
		order = Order.objects.create(client=self.customer)

		with self.assertRaisesMessage(ValidationError, 'Quantity must be greater than zero.'):
			OrderItem.objects.create(
				order=order,
				product=self.products[0],
				quantity=0,
				unit_price=self.products[0].unit_price,
			)

	def add_inventory(self, product, quantity, reserved=0):
		return Inventory.objects.create(product=product, quantity=quantity, reserved_quantity=reserved)

	def test_confirm_order_deducts_stock_and_records_reference(self):
		order = self.create_order((20, 0, 0))
		inventory = self.add_inventory(self.products[0], 100)

		confirm_order(order, user=self.staff)

		inventory.refresh_from_db()
		order.refresh_from_db()
		movement = StockMovement.objects.get()
		self.assertEqual(order.status, 'confirmed')
		self.assertEqual(inventory.quantity, 80)
		self.assertEqual(inventory.available_quantity, 80)
		self.assertEqual(movement.movement_type, StockMovement.MovementType.ISSUED)
		self.assertEqual(movement.quantity, 20)
		self.assertEqual(movement.reference, order.order_reference)

	def test_insufficient_stock_leaves_order_inventory_and_movements_unchanged(self):
		order = self.create_order((20, 0, 0))
		inventory = self.add_inventory(self.products[0], 10)

		with self.assertRaisesMessage(ValidationError, 'Insufficient stock for Water 1. Available: 10, Requested: 20.'):
			confirm_order(order)

		order.refresh_from_db()
		inventory.refresh_from_db()
		self.assertEqual(order.status, 'pending')
		self.assertEqual(inventory.quantity, 10)
		self.assertFalse(StockMovement.objects.exists())

	def test_reserved_units_are_not_available_for_confirmation(self):
		order = self.create_order((6, 0, 0))
		self.add_inventory(self.products[0], 10, reserved=5)

		with self.assertRaisesMessage(ValidationError, 'Available: 5, Requested: 6.'):
			confirm_order(order)

	def test_multiple_products_confirm_together(self):
		order = self.create_order((20, 10, 0))
		first = self.add_inventory(self.products[0], 100)
		second = self.add_inventory(self.products[1], 50)

		confirm_order(order)

		first.refresh_from_db()
		second.refresh_from_db()
		self.assertEqual((first.quantity, second.quantity), (80, 40))
		self.assertEqual(StockMovement.objects.count(), 2)

	def test_insufficient_second_product_does_not_partially_update(self):
		order = self.create_order((20, 10, 0))
		first = self.add_inventory(self.products[0], 100)
		second = self.add_inventory(self.products[1], 5)

		with self.assertRaisesMessage(ValidationError, 'Insufficient stock for Water 2. Available: 5, Requested: 10.'):
			confirm_order(order)

		order.refresh_from_db()
		first.refresh_from_db()
		second.refresh_from_db()
		self.assertEqual(order.status, 'pending')
		self.assertEqual((first.quantity, second.quantity), (100, 5))
		self.assertFalse(StockMovement.objects.exists())

	def test_missing_inventory_fails_safely(self):
		order = self.create_order((1, 0, 0))

		with self.assertRaisesMessage(ValidationError, 'Inventory record not found for Water 1.'):
			confirm_order(order)

		order.refresh_from_db()
		self.assertEqual(order.status, 'pending')
		self.assertFalse(StockMovement.objects.exists())

	def test_warehouse_prepares_only_confirmed_orders(self):
		order = self.create_order((1, 0, 0))
		self.add_inventory(self.products[0], 10)
		confirm_order(order, user=self.staff)
		warehouse = get_user_model().objects.create_user(username='prepare-warehouse', role='warehouse')

		prepared_order = prepare_order(order, acting_user=warehouse)

		self.assertEqual(prepared_order.status, 'preparing')
		with self.assertRaisesMessage(ValidationError, 'Only confirmed orders can be prepared.'):
			prepare_order(order, acting_user=warehouse)

	def test_sales_cannot_prepare_orders(self):
		order = self.create_order()
		sales = get_user_model().objects.create_user(username='prepare-sales', role='sales')

		with self.assertRaises(PermissionDenied):
			prepare_order(order, acting_user=sales)

	def test_cancelled_confirmed_order_restores_stock_and_records_return(self):
		order = self.create_order((20, 0, 0))
		inventory = self.add_inventory(self.products[0], 100)
		confirm_order(order, user=self.staff)

		cancel_order(order, user=self.staff)

		inventory.refresh_from_db()
		order.refresh_from_db()
		self.assertEqual(order.status, 'cancelled')
		self.assertEqual(inventory.quantity, 100)
		self.assertEqual(StockMovement.objects.count(), 2)
		self.assertEqual(
			StockMovement.objects.order_by('pk').last().movement_type,
			StockMovement.MovementType.RETURNED,
		)

	def test_confirm_view_shows_insufficient_stock_message(self):
		order = self.create_order((20, 0, 0))
		self.add_inventory(self.products[0], 10)

		response = self.client.post(reverse('order_confirm', args=[order.pk]), follow=True)

		self.assertRedirects(response, reverse('order_detail', args=[order.pk]))
		self.assertContains(response, 'Insufficient stock for Water 1. Available: 10, Requested: 20.')
