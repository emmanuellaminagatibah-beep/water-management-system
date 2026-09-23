from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from clients.models import Client
from deliveries.models import Driver


class Command(BaseCommand):
    help = 'Create or update one development user for each application role.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default='ChangeMe123!',
            help='Password assigned to the development users (change it outside local development).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']
        role_users = {
            'admin': ('admin', 'admin@example.com', True),
            'sales': ('sales', 'sales@example.com', False),
            'warehouse': ('warehouse', 'warehouse@example.com', False),
            'driver': ('driver', 'driver@example.com', False),
            'accounts': ('accounts', 'accounts@example.com', False),
            'client': ('client', 'client@example.com', False),
        }

        for role, (username, email, is_superuser) in role_users.items():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'role': role},
            )
            user.email = email
            user.role = role
            user.is_staff = is_superuser
            user.is_superuser = is_superuser
            user.is_active = True
            user.set_password(password)
            user.save()

            if role == 'driver':
                Driver.objects.get_or_create(user=user, defaults={'license_number': 'DEV-DRIVER-001'})
            elif role == 'client':
                Client.objects.get_or_create(
                    user=user,
                    defaults={'name': 'Development Client', 'email': email},
                )

            action = 'Created' if created else 'Updated'
            self.stdout.write(f'{action} {role} user: {username}')

        self.stdout.write(self.style.SUCCESS('Development role users are ready.'))