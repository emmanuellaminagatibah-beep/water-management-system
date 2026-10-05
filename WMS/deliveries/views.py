from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from clients.models import Client

from .forms import DeliveryScheduleForm, DriverDeliveryStatusForm, StaffDeliveryStatusForm
from .models import Delivery, Driver
from .services import change_delivery_status, schedule_delivery


@role_required('admin', 'sales', 'warehouse', 'driver')
def delivery_list(request):
	deliveries = Delivery.objects.select_related('order', 'driver', 'vehicle')
	if request.user.role == 'driver':
		deliveries = deliveries.filter(driver__user=request.user)
	return render(request, 'deliveries/delivery_list.html', {
		'deliveries': deliveries,
		'status_choices': Delivery.STATUS_CHOICES,
	})


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


@role_required('driver')
def driver_delivery_list(request):
	driver = get_object_or_404(Driver, user=request.user, is_active=True)
	deliveries = Delivery.objects.filter(driver=driver).select_related('order', 'order__client', 'vehicle').order_by('scheduled_date')
	return render(request, 'deliveries/driver_delivery_list.html', {'deliveries': deliveries})


@role_required('driver')
def driver_delivery_update(request, pk):
	driver = get_object_or_404(Driver, user=request.user, is_active=True)
	delivery = get_object_or_404(Delivery.objects.select_related('order', 'vehicle'), pk=pk, driver=driver)
	if request.method == 'POST':
		form = DriverDeliveryStatusForm(request.POST, instance=delivery)
		if form.is_valid():
			try:
				change_delivery_status(
					delivery=delivery,
					new_status=form.cleaned_data['status'],
					acting_user=request.user,
					status_note=form.cleaned_data['status_note'],
				)
			except ValidationError as error:
				form.add_error(None, error)
			except PermissionDenied:
				raise
			else:
				messages.success(request, 'Delivery status updated successfully.')
				return redirect('driver-delivery-list')
	else:
		form = DriverDeliveryStatusForm(instance=delivery)
	return render(request, 'deliveries/driver_delivery_update.html', {'delivery': delivery, 'form': form})


@role_required('client')
def client_delivery_list(request):
	client = get_object_or_404(Client, user=request.user)
	deliveries = Delivery.objects.filter(order__client=client).select_related('order', 'vehicle', 'driver').order_by('-scheduled_date')
	return render(request, 'deliveries/client_delivery_list.html', {'deliveries': deliveries})


@role_required('admin', 'sales')
def staff_delivery_update(request, pk):
	delivery = get_object_or_404(Delivery.objects.select_related('order', 'driver', 'vehicle'), pk=pk)
	if request.method == 'POST':
		form = StaffDeliveryStatusForm(request.POST, instance=delivery)
		if form.is_valid():
			try:
				change_delivery_status(
					delivery=delivery,
					new_status=form.cleaned_data['status'],
					acting_user=request.user,
					status_note=form.cleaned_data['status_note'],
				)
			except ValidationError as error:
				form.add_error(None, error)
			except PermissionDenied:
				raise
			else:
				messages.success(request, 'Delivery status updated successfully.')
				return redirect('delivery_list')
	else:
		form = StaffDeliveryStatusForm(instance=delivery)
	return render(request, 'deliveries/staff_delivery_update.html', {'delivery': delivery, 'form': form})


@role_required('admin', 'warehouse', 'driver')
@require_POST
def delivery_update_status(request, pk):
	delivery = get_object_or_404(Delivery.objects.select_related('driver__user'), pk=pk)
	if request.user.role == 'driver' and delivery.driver.user_id != request.user.id:
		return HttpResponseForbidden()

	status = request.POST.get('status')
	if status is None:
		messages.error(request, 'Choose a valid delivery status.')
		return redirect('delivery_list')
	status = status.strip().upper()
	if request.user.role == 'driver':
		allowed_statuses = {
			Delivery.Status.SCHEDULED: {Delivery.Status.DISPATCHED},
			Delivery.Status.DISPATCHED: {Delivery.Status.DELIVERED, Delivery.Status.FAILED},
		}.get(delivery.status, set())
	else:
		allowed_statuses = {value for value, _ in Delivery.Status.choices}
	if status in allowed_statuses:
		delivery.status = status
		if status == Delivery.Status.DELIVERED:
			delivery.delivered_at = timezone.now()
		delivery.save(update_fields=['status', 'delivered_at', 'updated_at'])
		messages.success(request, f'Delivery status updated to {delivery.get_status_display()}.')
	else:
		messages.error(request, 'Choose a valid delivery status.')
	return redirect('delivery_list')
