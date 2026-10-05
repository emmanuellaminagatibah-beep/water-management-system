from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from clients.models import Client

from .models import Complaint
from .services import update_complaint


class ComplaintWorkflowTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.client_user = get_user_model().objects.create_user(username='complaint-client', role='client')
		cls.sales_user = get_user_model().objects.create_user(username='complaint-sales', role='sales')
		cls.client_record = Client.objects.create(
			user=cls.client_user,
			client_id='COMP001',
			business_name='Complaint Customer',
			phone='0242000000',
			address='Accra',
		)
		cls.other_client = Client.objects.create(
			client_id='COMP002', business_name='Other Customer', phone='0242000001', address='Tema',
		)

	def test_customer_can_submit_and_only_view_their_complaints(self):
		own_complaint = Complaint.objects.create(
			client=self.client_record,
			subject='Late delivery',
			description='The delivery arrived late.',
		)
		other_complaint = Complaint.objects.create(
			client=self.other_client,
			subject='Other customer issue',
			description='Private customer details.',
		)
		self.client.force_login(self.client_user)
		response = self.client.get(reverse('complaint_list'))
		self.assertContains(response, own_complaint.subject)
		self.assertNotContains(response, other_complaint.subject)

		response = self.client.post(reverse('complaint_list'), {
			'order': '',
			'title': 'Water quality concern',
			'description': 'Please investigate this delivery.',
			'priority': 'high',
		})
		self.assertRedirects(response, reverse('complaint_list'))
		self.assertTrue(Complaint.objects.filter(client=self.client_record, title='Water quality concern').exists())

	def test_sales_can_update_complaint_status(self):
		complaint = Complaint.objects.create(
			client=self.client_record,
			subject='Update request',
			description='Please review.',
		)
		self.client.force_login(self.sales_user)

		response = self.client.post(reverse('complaint_update', args=[complaint.pk]), {
			'status': Complaint.Status.IN_PROGRESS,
			'priority': 'high',
			'assigned_staff': str(self.sales_user.pk),
			'staff_response': 'We are reviewing this request.',
		})

		self.assertRedirects(response, reverse('complaint_list'))
		complaint.refresh_from_db()
		self.assertEqual(complaint.status, Complaint.Status.IN_PROGRESS)
		self.assertEqual(complaint.assigned_staff, self.sales_user)
		self.assertEqual(complaint.staff_response, 'We are reviewing this request.')

	def test_complaint_transitions_are_enforced_and_resolved_date_is_set(self):
		complaint = Complaint.objects.create(
			client=self.client_record,
			title='State transition',
			description='Please review.',
		)
		with self.assertRaises(ValidationError):
			update_complaint(
				complaint=complaint,
				new_status=Complaint.Status.RESOLVED,
				assigned_staff=None,
				staff_response='Done',
				acting_user=self.sales_user,
			)
		complaint.refresh_from_db()
		self.assertEqual(complaint.status, Complaint.Status.OPEN)
		self.assertIsNone(complaint.resolved_date)

		update_complaint(
			complaint=complaint,
			new_status=Complaint.Status.IN_PROGRESS,
			assigned_staff=self.sales_user,
			staff_response='Working on it.',
			acting_user=self.sales_user,
		)
		complaint = update_complaint(
			complaint=complaint,
			new_status=Complaint.Status.RESOLVED,
			assigned_staff=self.sales_user,
			staff_response='Resolved.',
			acting_user=self.sales_user,
		)
		self.assertEqual(complaint.status, Complaint.Status.RESOLVED)
		self.assertIsNotNone(complaint.resolved_date)
