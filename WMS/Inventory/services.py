from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Inventory, StockMovement


INCREASE_TYPES = {
	StockMovement.MovementType.RECEIVED,
	StockMovement.MovementType.RETURNED,
}
DECREASE_TYPES = {
	StockMovement.MovementType.ISSUED,
	StockMovement.MovementType.DAMAGED,
}


@transaction.atomic
def adjust_stock(product, quantity, movement_type, user=None, note=''):
	if quantity <= 0:
		raise ValidationError('Quantity must be positive.')

	if movement_type not in INCREASE_TYPES and movement_type not in DECREASE_TYPES and movement_type != StockMovement.MovementType.OPENING:
		raise ValidationError(f'Unknown movement type: {movement_type}')

	inventory = Inventory.objects.select_for_update().get(product=product)

	if movement_type in INCREASE_TYPES or movement_type == StockMovement.MovementType.OPENING:
		inventory.quantity += quantity
	else:
		if inventory.quantity < quantity:
			raise ValidationError(
				f'Cannot remove {quantity} units - only {inventory.quantity} on hand.'
			)
		inventory.quantity -= quantity

	inventory.save(update_fields=['quantity', 'updated_at'])
	StockMovement.objects.create(
		product=product,
		movement_type=movement_type,
		quantity=quantity,
		created_by=user,
		note=note,
		reference=note,
	)
	return inventory