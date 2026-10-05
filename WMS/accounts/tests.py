from decimal import Decimal

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from billing.models import Invoice, Payment
from clients.models import Client
from complaints.models import Complaint
from deliveries.models import Delivery
from orders.models import Order

from .models import User


class AccountsViewsTests(TestCase):
    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_register_page_loads(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_password_is_stored_as_a_hash(self):
        user = User.objects.create_user(username='hashed-user', password='Secret123!')
        self.assertNotEqual(user.password, 'Secret123!')
        self.assertTrue(user.check_password('Secret123!'))

    def test_login_and_logout(self):
        User.objects.create_user(username='login-user', password='Secret123!')

        login_response = self.client.post(
            reverse('login'),
            {'username': 'login-user', 'password': 'Secret123!'},
        )
        self.assertRedirects(login_response, reverse('dashboard'))

        logout_response = self.client.get(reverse('logout'))
        self.assertRedirects(logout_response, reverse('login'))

    def test_invalid_login_shows_error_without_authenticating(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'missing-user', 'password': 'incorrect-password'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password.')
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f'{reverse("login")}?next={reverse("dashboard")}')


class DemoSeedCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_demo_command_builds_full_flow_and_is_idempotent(self):
        call_command('seed_demo_data', verbosity=0)
        call_command('seed_demo_data', verbosity=0)

        order = Order.objects.get(notes='DEMO-FLOW-001')
        delivery = Delivery.objects.get(order=order)
        invoice = Invoice.objects.get(order=order)
        client = Client.objects.get(client_id='DEMO-CLIENT-001')

        self.assertEqual(order.status, 'delivered')
        self.assertEqual(delivery.status, Delivery.Status.DELIVERED)
        self.assertEqual(invoice.payment_status, Invoice.PaymentStatus.PARTIALLY_PAID)
        self.assertEqual(invoice.total_amount, Decimal('30.00'))
        self.assertEqual(invoice.outstanding_balance, Decimal('20.00'))
        self.assertEqual(invoice.payments.filter(reference='DEMO-RECEIPT-001').count(), 1)
        self.assertEqual(Complaint.objects.filter(client=client, title='Demo delivery feedback').count(), 1)
        self.assertEqual(User.objects.filter(username__startswith='demo_').count(), 6)
        self.assertEqual(order.deliveries.count(), 1)
        self.assertEqual(invoice.items.count(), 1)

    @override_settings(DEBUG=False)
    def test_demo_command_refuses_to_create_known_password_accounts_in_production(self):
        with self.assertRaisesMessage(CommandError, 'Demo accounts can only be created while DJANGO_DEBUG is enabled.'):
            call_command('seed_demo_data', verbosity=0)
