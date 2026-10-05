from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from products.models import Product

from .models import Inventory, StockMovement
from .services import adjust_stock


class AdjustStockTests(TestCase):
	def setUp(self):
		self.product = Product.objects.create(
			sku='SACHET-500',
			name='Sachet Water 500ml',
		)
		self.inventory = Inventory.objects.create(
			product=self.product,
			reorder_level=10,
		)

	def test_received_increases_stock_and_records_movement(self):
		adjust_stock(self.product, 50, StockMovement.MovementType.RECEIVED)

		self.inventory.refresh_from_db()
		self.assertEqual(self.inventory.quantity_on_hand, 50)
		self.assertEqual(StockMovement.objects.count(), 1)

	def test_issued_decreases_stock(self):
		adjust_stock(self.product, 50, StockMovement.MovementType.RECEIVED)
		adjust_stock(self.product, 20, StockMovement.MovementType.ISSUED)

		self.inventory.refresh_from_db()
		self.assertEqual(self.inventory.quantity_on_hand, 30)

	def test_issuing_more_than_available_raises(self):
		with self.assertRaises(ValidationError):
			adjust_stock(self.product, 5, StockMovement.MovementType.ISSUED)

	def test_low_stock_flag_and_queryset(self):
		adjust_stock(self.product, 10, StockMovement.MovementType.RECEIVED)
		self.inventory.refresh_from_db()

		self.assertTrue(self.inventory.is_low_stock)
		self.assertIn(self.inventory, Inventory.objects.low_stock())

	def test_non_positive_quantity_raises(self):
		with self.assertRaises(ValidationError):
			adjust_stock(self.product, 0, StockMovement.MovementType.RECEIVED)

	def test_warehouse_can_record_stock_movement(self):
		warehouse_user = get_user_model().objects.create_user(username='inventory-warehouse', role='warehouse')
		self.client.force_login(warehouse_user)

		response = self.client.post(reverse('stock-movement-create'), {
			'product': self.product.pk,
			'movement_type': StockMovement.MovementType.RECEIVED,
			'quantity': '25',
			'note': 'Morning delivery',
			'reference': 'GRN-001',
		})

		self.assertRedirects(response, reverse('inventory-list'))
		self.inventory.refresh_from_db()
		self.assertEqual(self.inventory.quantity, 25)
		self.assertEqual(StockMovement.objects.get().created_by, warehouse_user)

	def test_sales_cannot_record_stock_movement(self):
		sales_user = get_user_model().objects.create_user(username='inventory-sales', role='sales')
		self.client.force_login(sales_user)

		response = self.client.get(reverse('stock-movement-create'))

		self.assertEqual(response.status_code, 403)
