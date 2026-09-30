from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clients.models import Client
from orders.models import Order

from .forms import DeliveryScheduleForm
from .models import Delivery, Driver, Vehicle
from .services import schedule_delivery


class DeliverySchedulingTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		user_model = get_user_model()
		cls.sales_user = user_model.objects.create_user(
			username='delivery-sales', password='test-password', role='sales'
		)
		cls.driver_user = user_model.objects.create_user(
			username='delivery-driver', password='test-password', role='driver'
		)
		cls.customer = Client.objects.create(
			client_id='DEL001', business_name='Delivery Customer', phone='0240000001', address='Accra'
		)
		cls.order = Order.objects.create(client=cls.customer, status='confirmed')
		cls.driver = Driver.objects.create(
			user=cls.driver_user, name='Ama Driver', phone='0240000002', license_number='DL-001'
		)
		cls.vehicle = Vehicle.objects.create(
			registration_number='GT-001-26', vehicle_type='Tanker', capacity_litres=5000
		)

	def schedule(self, **overrides):
		values = {
			'order': self.order,
			'driver': self.driver,
			'vehicle': self.vehicle,
			'destination': 'Accra Central',
			'scheduled_date': timezone.now() + timedelta(days=1),
		}
		values.update(overrides)
		return schedule_delivery(**values)

	def test_active_driver_and_vehicle_schedule_confirmed_order(self):
		delivery = self.schedule()

		self.assertEqual(delivery.status, 'scheduled')
		self.assertEqual(Delivery.objects.get(pk=delivery.pk).order, self.order)

	def test_inactive_driver_cannot_be_assigned(self):
		self.driver.is_active = False
		self.driver.save()

		with self.assertRaises(ValidationError) as error:
			self.schedule()

		self.assertIn('driver', error.exception.message_dict)

	def test_inactive_or_maintenance_vehicle_cannot_be_assigned(self):
		for status in ('inactive', 'maintenance'):
			with self.subTest(status=status):
				self.vehicle.status = status
				self.vehicle.save()
				with self.assertRaises(ValidationError) as error:
					self.schedule()
				self.assertIn('vehicle', error.exception.message_dict)

	def test_pending_order_cannot_be_scheduled(self):
		self.order.status = 'pending'
		self.order.save()

		with self.assertRaises(ValidationError) as error:
			self.schedule()

		self.assertIn('order', error.exception.message_dict)

	def test_sales_user_can_open_create_page(self):
		self.client.force_login(self.sales_user)

		response = self.client.get(reverse('delivery_create'))

		self.assertEqual(response.status_code, 200)
		self.assertIsInstance(response.context['form'], DeliveryScheduleForm)

	def test_driver_user_cannot_open_create_page(self):
		self.client.force_login(self.driver_user)

		response = self.client.get(reverse('delivery_create'))

		self.assertEqual(response.status_code, 403)

	def test_form_only_offers_active_drivers_vehicles_and_schedulable_orders(self):
		inactive_driver = Driver.objects.create(name='Inactive Driver', license_number='DL-002', is_active=False)
		inactive_vehicle = Vehicle.objects.create(registration_number='GT-002-26', status='inactive')
		pending_order = Order.objects.create(client=self.customer, status='pending')
		form = DeliveryScheduleForm()

		self.assertNotIn(inactive_driver, form.fields['driver'].queryset)
		self.assertNotIn(inactive_vehicle, form.fields['vehicle'].queryset)
		self.assertNotIn(pending_order, form.fields['order'].queryset)
