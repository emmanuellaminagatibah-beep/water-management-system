from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import transaction

from Inventory.models import Inventory, StockMovement
from Inventory.services import adjust_stock

from .models import Order


def _locked_order(order):
	return Order.objects.select_for_update().get(pk=order.pk if isinstance(order, Order) else order)


def _order_quantities(order):
	quantities = defaultdict(int)
	products = {}
	for item in order.items.select_related('product').order_by('product_id'):
		if item.quantity <= 0:
			raise ValidationError(f'Quantity for {item.product.name} must be greater than zero.')
		quantities[item.product_id] += item.quantity
		products[item.product_id] = item.product
	if not quantities:
		raise ValidationError('An order must contain at least one product.')
	return quantities, products


@transaction.atomic
def confirm_order(order, user=None):
	order = _locked_order(order)
	if order.status != 'pending':
		raise ValidationError('Only pending orders can be confirmed.')

	quantities, products = _order_quantities(order)
	inventories = {
		inventory.product_id: inventory
		for inventory in Inventory.objects.select_for_update()
		.select_related('product')
		.filter(product_id__in=quantities)
	}

	for product_id, requested in quantities.items():
		product = products[product_id]
		inventory = inventories.get(product_id)
		if inventory is None:
			raise ValidationError(f'Inventory record not found for {product.name}.')
		available = inventory.available_quantity
		if requested > available:
			raise ValidationError(
				f'Insufficient stock for {product.name}. Available: {available}, Requested: {requested}.'
			)

	for product_id, requested in quantities.items():
		adjust_stock(
			products[product_id],
			requested,
			StockMovement.MovementType.ISSUED,
			user=user,
			note=f'Order {order.order_reference} confirmed',
			reference=order.order_reference,
		)

	order.status = 'confirmed'
	order.save(update_fields=['status'])
	return order


@transaction.atomic
def cancel_order(order, user=None):
	order = _locked_order(order)
	if order.status != 'confirmed':
		raise ValidationError('Only confirmed orders can be cancelled.')

	quantities, products = _order_quantities(order)
	for product_id, requested in quantities.items():
		if not Inventory.objects.select_for_update().filter(product_id=product_id).exists():
			raise ValidationError(f'Inventory record not found for {products[product_id].name}.')
		adjust_stock(
			products[product_id],
			requested,
			StockMovement.MovementType.RETURNED,
			user=user,
			note=f'Order {order.order_reference} cancelled',
			reference=order.order_reference,
		)

	order.status = 'cancelled'
	order.save(update_fields=['status'])
	return order