from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from accounts.decorators import role_required

from .forms import DeliveryScheduleForm
from .models import Delivery
from .services import schedule_delivery


@role_required('admin', 'sales', 'warehouse')
def delivery_list(request):
	deliveries = Delivery.objects.select_related('order', 'driver', 'vehicle')
	return render(request, 'deliveries/delivery_list.html', {'deliveries': deliveries})


@role_required('admin', 'sales')
def delivery_create(request):
	form = DeliveryScheduleForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		try:
			delivery = schedule_delivery(**form.cleaned_data)
		except ValidationError as error:
			for field, field_errors in error.error_dict.items():
				for field_error in field_errors:
					form.add_error(field, field_error)
		else:
			messages.success(request, f'Delivery for {delivery.order.order_reference} was scheduled.')
			return redirect('delivery_list')
	return render(request, 'deliveries/delivery_form.html', {'form': form})
