from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from clients.models import Client
from products.models import Product

from .models import Order, OrderItem


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
			'status': 'confirmed',
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
		self.assertEqual(order.status, 'confirmed')
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
