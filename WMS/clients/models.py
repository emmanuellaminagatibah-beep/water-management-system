from django.db import models
from accounts.models import User


class Client(models.Model):

    CATEGORY_CHOICES = [
        ('individual', 'Individual'),
        ('business', 'Business'),
        ('institution', 'Institution'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='client_profile',
        null=True,
        blank=True
    )

    client_id = models.CharField(
        max_length=20,
        unique=True
    )

    business_name = models.CharField(
        max_length=150,
        blank=True
    )

    phone = models.CharField(
        max_length=20
    )

    email = models.EmailField(
        blank=True
    )

    address = models.TextField()

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='individual'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.client_id} - {self.business_name or self.phone}"