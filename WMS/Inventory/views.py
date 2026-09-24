from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Inventory, StockMovement


@login_required
def inventory_list(request):
	items = Inventory.objects.select_related('product').all()
	return render(request, 'inventory/inventory_list.html', {'items': items})


@login_required
def stock_movement_history(request):
	movements = StockMovement.objects.select_related('product', 'created_by').all()
	movement_type = request.GET.get('type')
	if movement_type:
		movements = movements.filter(movement_type=movement_type)

	product_id = request.GET.get('product')
	if product_id:
		movements = movements.filter(product_id=product_id)

	return render(request, 'inventory/movement_history.html', {'movements': movements})
