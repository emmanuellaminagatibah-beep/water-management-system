from django.conf import settings
from django.db import models


class Client(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='client_profile',
	)
	name = models.CharField(max_length=150)
	email = models.EmailField(blank=True)
	phone = models.CharField(max_length=20, blank=True)
	address = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name
