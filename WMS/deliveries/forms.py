from django import forms

from orders.models import Order

from .models import Delivery, Driver, Vehicle


class DeliveryScheduleForm(forms.ModelForm):
	class Meta:
		model = Delivery
		fields = ('order', 'driver', 'vehicle', 'destination', 'scheduled_date')
		widgets = {
			'scheduled_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['order'].queryset = Order.objects.filter(status__in=('confirmed', 'preparing'))
		self.fields['driver'].queryset = Driver.objects.filter(is_active=True)
		self.fields['vehicle'].queryset = Vehicle.objects.filter(status='active', is_active=True)