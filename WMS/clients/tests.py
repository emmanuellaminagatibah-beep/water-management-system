from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Client


class ClientAccessTests(TestCase):
	def test_sales_can_create_client_and_warehouse_is_forbidden(self):
		sales_user = get_user_model().objects.create_user(username='client-sales', role='sales')
		self.client.force_login(sales_user)
		response = self.client.post(reverse('client_create'), {
			'client_id': 'CLIENT-NEW',
			'business_name': 'New Water Customer',
			'phone': '0245000000',
			'email': 'customer@example.com',
			'address': 'Accra',
			'category': 'business',
			'status': 'active',
		})
		self.assertRedirects(response, reverse('client_list'))
		self.assertTrue(Client.objects.filter(client_id='CLIENT-NEW').exists())

		warehouse_user = get_user_model().objects.create_user(username='client-warehouse', role='warehouse')
		self.client.force_login(warehouse_user)
		self.assertEqual(self.client.get(reverse('client_create')).status_code, 403)
		self.assertEqual(self.client.get(reverse('client_list')).status_code, 403)

	def test_client_can_create_and_edit_only_their_own_profile(self):
		user = get_user_model().objects.create_user(username='profile-client', role='client')
		self.client.force_login(user)
		response = self.client.post(reverse('client_portal'), {
			'business_name': 'Portal Customer',
			'phone': '0245000001',
			'email': 'portal@example.com',
			'address': 'Tema',
			'category': 'individual',
		})
		self.assertRedirects(response, reverse('client_portal'))
		profile = Client.objects.get(user=user)
		self.assertTrue(profile.client_id.startswith('WEB-'))
		self.assertEqual(profile.business_name, 'Portal Customer')
