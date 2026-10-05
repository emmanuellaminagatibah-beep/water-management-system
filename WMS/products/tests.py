from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Product


class ProductCatalogTests(TestCase):
	def test_catalog_shows_active_products_to_authorized_roles_only(self):
		Product.objects.create(sku='CATALOG-ACTIVE', name='Available water', is_active=True)
		Product.objects.create(sku='CATALOG-ARCHIVED', name='Archived water', is_active=False)
		warehouse_user = get_user_model().objects.create_user(username='catalog-warehouse', role='warehouse')
		self.client.force_login(warehouse_user)

		response = self.client.get(reverse('product_catalog'))
		self.assertContains(response, 'Available water')
		self.assertNotContains(response, 'Archived water')

		driver_user = get_user_model().objects.create_user(username='catalog-driver', role='driver')
		self.client.force_login(driver_user)
		self.assertEqual(self.client.get(reverse('product_catalog')).status_code, 403)
