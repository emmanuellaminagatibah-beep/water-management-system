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


class StaffDeliveryStatusForm(forms.ModelForm):
	class Meta:
		model = Delivery
		fields = ('status', 'status_note')
		widgets = {
			'status_note': forms.Textarea(attrs={
				'rows': 4,
				'placeholder': 'Optional cancellation or dispatch note',
			}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['status'].choices = [
			(Delivery.Status.DISPATCHED, 'Dispatched'),
			(Delivery.Status.CANCELLED, 'Cancelled'),
		]


class DriverDeliveryStatusForm(forms.ModelForm):
	class Meta:
		model = Delivery
		fields = ('status', 'status_note')
		widgets = {
			'status_note': forms.Textarea(attrs={
				'rows': 4,
				'placeholder': 'Add a delivery result or failure reason',
			}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['status'].choices = [
			(Delivery.Status.DELIVERED, 'Delivered'),
			(Delivery.Status.PARTIALLY_DELIVERED, 'Partially delivered'),
			(Delivery.Status.FAILED, 'Failed'),
		]