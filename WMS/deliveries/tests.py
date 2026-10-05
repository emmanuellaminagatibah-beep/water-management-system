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

	def test_driver_only_sees_and_updates_assigned_deliveries(self):
		own_delivery = self.schedule()
		other_user = get_user_model().objects.create_user(username='another-driver', role='driver')
		other_driver = Driver.objects.create(user=other_user, name='Other Driver', license_number='DL-003')
		other_order = Order.objects.create(client=self.customer, status='confirmed')
		other_delivery = self.schedule(driver=other_driver, order=other_order)
		self.client.force_login(self.driver_user)

		response = self.client.get(reverse('delivery_list'))

		self.assertContains(response, own_delivery.order.order_reference)
		self.assertNotContains(response, other_delivery.order.order_reference)
		update_response = self.client.post(
			reverse('delivery_update_status', args=[own_delivery.pk]),
			{'status': 'in_transit'},
		)
		own_delivery.refresh_from_db()
		self.assertEqual(update_response.status_code, 302)
		self.assertEqual(own_delivery.status, 'in_transit')

	def test_driver_cannot_update_another_drivers_delivery(self):
		other_user = get_user_model().objects.create_user(username='unassigned-driver', role='driver')
		other_driver = Driver.objects.create(user=other_user, name='Other Driver', license_number='DL-004')
		delivery = self.schedule(driver=other_driver)
		self.client.force_login(self.driver_user)

		response = self.client.post(
			reverse('delivery_update_status', args=[delivery.pk]),
			{'status': 'delivered'},
		)

		self.assertEqual(response.status_code, 403)

	def test_form_only_offers_active_drivers_vehicles_and_schedulable_orders(self):
		inactive_driver = Driver.objects.create(name='Inactive Driver', license_number='DL-002', is_active=False)
		inactive_vehicle = Vehicle.objects.create(registration_number='GT-002-26', status='inactive')
		pending_order = Order.objects.create(client=self.customer, status='pending')
		form = DeliveryScheduleForm()

		self.assertNotIn(inactive_driver, form.fields['driver'].queryset)
		self.assertNotIn(inactive_vehicle, form.fields['vehicle'].queryset)
		self.assertNotIn(pending_order, form.fields['order'].queryset)


class DeliveryDay8WorkflowTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		user_model = get_user_model()
		cls.sales_user = user_model.objects.create_user(username='sales-day8', password='test-password', role='sales')
		cls.driver_user = user_model.objects.create_user(username='driver-day8', password='test-password', role='driver')
		cls.client_user = user_model.objects.create_user(username='client-day8', password='test-password', role='client')
		cls.other_client_user = user_model.objects.create_user(username='other-client-day8', password='test-password', role='client')
		cls.client = Client.objects.create(client_id='CLD-001', business_name='Acme Water', phone='0240000001', address='Kumasi', user=cls.client_user)
		cls.other_client = Client.objects.create(client_id='CLD-002', business_name='Other Client', phone='0240000002', address='Tamale', user=cls.other_client_user)
		cls.driver = Driver.objects.create(user=cls.driver_user, name='Day 8 Driver', phone='0240000003', license_number='DL-900')
		cls.vehicle = Vehicle.objects.create(registration_number='GV-900-26', vehicle_type='Truck', capacity_litres=2000, status='active', is_active=True)
		cls.order = Order.objects.create(client=cls.client, status='confirmed')
		cls.other_order = Order.objects.create(client=cls.other_client, status='confirmed')

	def test_sales_dispatches_then_driver_fully_completes_delivery(self):
		delivery = schedule_delivery(
			order=self.order,
			driver=self.driver,
			vehicle=self.vehicle,
			destination='Kumasi Central',
			scheduled_date=timezone.now() + timedelta(days=1),
		)
		self.client.force_login(self.sales_user)
		response = self.client.post(
			reverse('staff-delivery-update', args=[delivery.pk]),
			{'status': 'DISPATCHED', 'status_note': 'En route'},
		)
		self.assertEqual(response.status_code, 302)
		delivery.refresh_from_db()
		self.assertEqual(delivery.status, 'DISPATCHED')
		self.assertEqual(delivery.status_note, 'En route')

		self.client.force_login(self.driver_user)
		response = self.client.post(
			reverse('driver-delivery-update', args=[delivery.pk]),
			{'status': 'DELIVERED', 'status_note': 'Delivered to customer'},
		)
		self.assertEqual(response.status_code, 302)
		delivery.refresh_from_db()
		self.assertEqual(delivery.status, 'DELIVERED')
		self.assertIsNotNone(delivery.completed_at)

	def test_client_only_sees_own_delivery_records(self):
		self.client.force_login(self.client_user)
		own_delivery = schedule_delivery(
			order=self.order,
			driver=self.driver,
			vehicle=self.vehicle,
			destination='Kumasi Central',
			scheduled_date=timezone.now() + timedelta(days=2),
		)
		schedule_delivery(
			order=self.other_order,
			driver=self.driver,
			vehicle=self.vehicle,
			destination='Tamale Central',
			scheduled_date=timezone.now() + timedelta(days=3),
		)
		response = self.client.get(reverse('client-delivery-list'))
		self.assertContains(response, own_delivery.order.order_reference)
		self.assertNotContains(response, 'Tamale Central')
