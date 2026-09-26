from django import forms
from django.forms import inlineformset_factory

from clients.models import Client
from products.models import Product

from .models import Order, OrderItem


class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['client']

    client = forms.ModelChoiceField(queryset=Client.objects.order_by('client_id'))


class OrderEditForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['client', 'status']

    client = forms.ModelChoiceField(queryset=Client.objects.order_by('client_id'))


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']

    product = forms.ModelChoiceField(queryset=Product.objects.order_by('name'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_product_id = self.instance.product_id

    def save(self, commit=True):
        item = super().save(commit=False)
        product = self.cleaned_data['product']
        if item.pk is None or self.original_product_id != product.pk:
            item.unit_price = product.unit_price
        item.product = product
        if commit:
            item.save()
        return item


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    fields=['product', 'quantity'],
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
