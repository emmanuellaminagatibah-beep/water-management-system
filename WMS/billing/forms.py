from decimal import Decimal

from django import forms
from django.core.validators import MinValueValidator

from deliveries.models import Delivery
from orders.models import Order

from .models import Invoice, Payment


class InvoiceCreateForm(forms.ModelForm):
	due_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

	class Meta:
		model = Invoice
		fields = ('order', 'due_date')
		widgets = {'due_date': forms.DateInput(attrs={'type': 'date'})}

	order = forms.ModelChoiceField(
		queryset=Order.objects.filter(
			status='delivered',
			deliveries__status=Delivery.Status.DELIVERED,
		).distinct(),
	)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['order'].queryset = self.fields['order'].queryset.exclude(
			invoice__isnull=False,
		).select_related('client')


class PaymentForm(forms.ModelForm):
	class Meta:
		model = Payment
		fields = ('amount', 'method', 'reference')

	amount = forms.DecimalField(
		max_digits=12,
		decimal_places=2,
		validators=[MinValueValidator(Decimal('0.01'))],
	)
