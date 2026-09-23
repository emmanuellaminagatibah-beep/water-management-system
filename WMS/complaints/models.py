from django.conf import settings
from django.db import models


class Complaint(models.Model):
	STATUS_CHOICES = [
		('open', 'Open'),
		('in_progress', 'In progress'),
		('resolved', 'Resolved'),
		('closed', 'Closed'),
	]
	PRIORITY_CHOICES = [
		('low', 'Low'),
		('medium', 'Medium'),
		('high', 'High'),
	]

	client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='complaints')
	order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
	subject = models.CharField(max_length=150)
	description = models.TextField()
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
	priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
	assigned_to = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='assigned_complaints',
	)
	created_at = models.DateTimeField(auto_now_add=True)
	resolved_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.subject
