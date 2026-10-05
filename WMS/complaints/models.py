from django.conf import settings
from django.db import models


class Complaint(models.Model):
	class Status(models.TextChoices):
		OPEN = 'OPEN', 'Open'
		IN_PROGRESS = 'IN_PROGRESS', 'In progress'
		RESOLVED = 'RESOLVED', 'Resolved'
		CLOSED = 'CLOSED', 'Closed'

	STATUS_CHOICES = Status.choices
	PRIORITY_CHOICES = [
		('low', 'Low'),
		('medium', 'Medium'),
		('high', 'High'),
	]

	client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='complaints')
	order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
	title = models.CharField(max_length=150)
	description = models.TextField()
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=Status.OPEN)
	priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
	staff_response = models.TextField(blank=True)
	assigned_staff = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='assigned_complaints',
	)
	created_at = models.DateTimeField(auto_now_add=True)
	resolved_at = models.DateTimeField(null=True, blank=True)
	resolved_date = models.DateField(null=True, blank=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.title

	@property
	def subject(self):
		return self.title

	@subject.setter
	def subject(self, value):
		self.title = value

	@property
	def assigned_to(self):
		return self.assigned_staff

	@assigned_to.setter
	def assigned_to(self, value):
		self.assigned_staff = value

	def save(self, *args, **kwargs):
		if self.status:
			self.status = str(self.status).upper()
		super().save(*args, **kwargs)
