from django import forms

from .models import Client


class ClientProfileForm(forms.ModelForm):
	class Meta:
		model = Client
		fields = ('business_name', 'phone', 'email', 'address', 'category')


class ClientCreateForm(forms.ModelForm):
	class Meta:
		model = Client
		fields = ('client_id', 'business_name', 'phone', 'email', 'address', 'category', 'status')
