from django.test import TestCase
from django.urls import reverse

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

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f'{reverse("login")}?next={reverse("dashboard")}')
