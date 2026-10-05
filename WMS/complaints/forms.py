from django import forms

from accounts.models import User
from orders.models import Order

from .models import Complaint
from .services import VALID_TRANSITIONS


class ComplaintCreateForm(forms.ModelForm):
	class Meta:
		model = Complaint
		fields = ('order', 'title', 'description', 'priority')

	order = forms.ModelChoiceField(queryset=Order.objects.none(), required=False)

	def __init__(self, *args, client=None, **kwargs):
		super().__init__(*args, **kwargs)
		if client:
			self.fields['order'].queryset = Order.objects.filter(client=client).order_by('-created_at')


class ComplaintUpdateForm(forms.ModelForm):
	class Meta:
		model = Complaint
		fields = ('status', 'priority', 'assigned_staff', 'staff_response')

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['assigned_staff'].queryset = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SALES]).order_by('username')
		if self.instance and self.instance.pk:
			allowed = {self.instance.status, *VALID_TRANSITIONS[self.instance.status]}
			self.fields['status'].choices = [choice for choice in Complaint.Status.choices if choice[0] in allowed]
