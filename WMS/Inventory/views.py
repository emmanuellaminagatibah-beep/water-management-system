from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import role_required

from .forms import StockMovementForm
from .models import Inventory, StockMovement
from .services import adjust_stock


@role_required('admin', 'warehouse', 'accounts')
def inventory_list(request):
	items = Inventory.objects.select_related('product').all()
	return render(request, 'inventory/inventory_list.html', {'items': items})


@role_required('admin', 'warehouse', 'accounts')
def stock_movement_history(request):
	movements = StockMovement.objects.select_related('product', 'created_by').all()
	movement_type = request.GET.get('type')
	if movement_type:
		movements = movements.filter(movement_type=movement_type)

	product_id = request.GET.get('product')
	if product_id:
		movements = movements.filter(product_id=product_id)

	return render(request, 'inventory/movement_history.html', {'movements': movements})


@role_required('admin', 'warehouse')
@require_http_methods(['GET', 'POST'])
def stock_movement_create(request):
	form = StockMovementForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		product = form.cleaned_data['product']
		Inventory.objects.get_or_create(product=product, defaults={'reorder_level': product.reorder_level})
		try:
			adjust_stock(
				product=product,
				quantity=form.cleaned_data['quantity'],
				movement_type=form.cleaned_data['movement_type'],
				user=request.user,
				note=form.cleaned_data['note'],
				reference=form.cleaned_data['reference'],
			)
		except ValidationError as error:
			form.add_error(None, error.messages[0])
		else:
			messages.success(request, 'Stock movement recorded.')
			return redirect('inventory-list')
	return render(request, 'inventory/stock_movement_form.html', {'form': form})
