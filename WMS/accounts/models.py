from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        SALES = 'sales', 'Sales Staff'
        WAREHOUSE = 'warehouse', 'Warehouse Staff'
        DRIVER = 'driver', 'Driver'
        ACCOUNTS = 'accounts', 'Accounts Staff'
        CLIENT = 'client', 'Client'

    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('sales', 'Sales Staff'),
        ('warehouse', 'Warehouse Staff'),
        ('driver', 'Driver'),
        ('accounts', 'Accounts Staff'),
        ('client', 'Client'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='client'
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    def __str__(self):
        return self.username