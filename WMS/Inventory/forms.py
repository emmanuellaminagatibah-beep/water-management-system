from django import forms
from django.core.validators import MinValueValidator

from products.models import Product

from .models import StockMovement


class StockMovementForm(forms.Form):
	product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True).order_by('name'))
	movement_type = forms.ChoiceField(choices=(
		(StockMovement.MovementType.RECEIVED, 'Stock received'),
		(StockMovement.MovementType.ISSUED, 'Stock issued'),
		(StockMovement.MovementType.DAMAGED, 'Damaged stock'),
		(StockMovement.MovementType.RETURNED, 'Returned stock'),
	))
	quantity = forms.IntegerField(validators=[MinValueValidator(1)])
	note = forms.CharField(max_length=255, required=False)
	reference = forms.CharField(max_length=120, required=False)
