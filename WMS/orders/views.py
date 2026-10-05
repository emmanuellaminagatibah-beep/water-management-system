from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from clients.models import Client

from accounts.decorators import role_required

from .forms import OrderCreateForm, OrderEditForm, OrderItemFormSet
from .models import Order
from .services import cancel_order, confirm_order, prepare_order


order_viewer_required = user_passes_test(
	lambda user: user.is_staff or user.is_superuser
	or user.role in {'admin', 'sales', 'accounts', 'warehouse'}
)
order_editor_required = user_passes_test(
	lambda user: user.is_staff or user.is_superuser or user.role in {'admin', 'sales'}
)
order_confirmer_required = user_passes_test(
	lambda user: user.is_staff or user.is_superuser or user.role in {'admin', 'sales', 'warehouse'}
)


@login_required
@order_viewer_required
def order_list(request):
	orders = Order.objects.select_related('client')
	search = request.GET.get('q', '').strip()
	status = request.GET.get('status', '')
	created_on = request.GET.get('created_on', '')

	if search:
		orders = orders.filter(
			Q(order_reference__icontains=search)
			| Q(client__client_id__icontains=search)
			| Q(client__business_name__icontains=search)
			| Q(client__phone__icontains=search)
		)
	if status in dict(Order.STATUS_CHOICES):
		orders = orders.filter(status=status)
	if created_on:
		orders = orders.filter(created_at__date=created_on)

	return render(request, 'orders/order_list.html', {
		'orders': orders,
		'search': search,
		'selected_status': status,
		'created_on': created_on,
		'status_choices': Order.STATUS_CHOICES,
	})


@login_required
@order_editor_required
def order_create(request):
	order_form = OrderCreateForm(request.POST or None)
	item_formset = OrderItemFormSet(request.POST or None)

	if request.method == 'POST' and order_form.is_valid() and item_formset.is_valid():
		with transaction.atomic():
			order = order_form.save(commit=False)
			order.status = 'pending'
			order.created_by = request.user
			order.save()
			item_formset.instance = order
			item_formset.save()
		messages.success(request, f'Order {order.order_reference} was created.')
		return redirect('order_detail', pk=order.pk)

	return render(request, 'orders/order_form.html', {
		'order_form': order_form,
		'item_formset': item_formset,
		'page_title': 'Create order',
		'is_create': True,
	})


@login_required
@order_editor_required
def order_edit(request, pk):
	order = get_object_or_404(Order.objects.select_related('client'), pk=pk)
	if order.status != 'pending':
		messages.error(request, 'Only pending orders can be edited.')
		return redirect('order_detail', pk=order.pk)
	order_form = OrderEditForm(request.POST or None, instance=order)
	item_formset = OrderItemFormSet(request.POST or None, instance=order)

	if request.method == 'POST' and order_form.is_valid() and item_formset.is_valid():
		with transaction.atomic():
			order_form.save()
			item_formset.save()
			order.recalculate_total()
		messages.success(request, f'Order {order.order_reference} was updated.')
		return redirect('order_detail', pk=order.pk)

	return render(request, 'orders/order_form.html', {
		'order': order,
		'order_form': order_form,
		'item_formset': item_formset,
		'page_title': f'Edit {order.order_reference}',
		'is_create': False,
	})


@login_required
@order_viewer_required
def order_detail(request, pk):
	order = get_object_or_404(
		Order.objects.select_related('client').prefetch_related('items__product'),
		pk=pk,
	)
	return render(request, 'orders/order_detail.html', {'order': order})


@login_required
@order_confirmer_required
@require_POST
def order_confirm(request, pk):
	order = get_object_or_404(Order, pk=pk)
	try:
		confirm_order(order, user=request.user)
	except ValidationError as error:
		messages.error(request, error.messages[0])
	else:
		messages.success(request, f'Order {order.order_reference} confirmed successfully.')
	return redirect('order_detail', pk=order.pk)


@login_required
@role_required('admin', 'warehouse')
@require_POST
def order_prepare(request, pk):
	order = get_object_or_404(Order, pk=pk)
	try:
		prepare_order(order, acting_user=request.user)
	except ValidationError as error:
		messages.error(request, error.messages[0])
	else:
		messages.success(request, f'Order {order.order_reference} is ready for dispatch.')
	return redirect('order_detail', pk=order.pk)


@login_required
@order_editor_required
@require_POST
def order_cancel(request, pk):
	order = get_object_or_404(Order, pk=pk)
	try:
		cancel_order(order, user=request.user)
	except ValidationError as error:
		messages.error(request, error.messages[0])
	else:
		messages.success(request, f'Order {order.order_reference} cancelled successfully.')
	return redirect('order_detail', pk=order.pk)


@login_required
@role_required('client')
def my_orders(request):
	client = Client.objects.filter(user=request.user).first()
	orders = Order.objects.filter(client=client) if client else Order.objects.none()
	return render(request, 'orders/my_orders.html', {'orders': orders, 'client': client})


@login_required
@role_required('client')
def client_order_create(request):
	client = Client.objects.filter(user=request.user).first()
	if client is None:
		return redirect('client_portal')
	order_form = OrderCreateForm(request.POST or None, initial={'client': client})
	order_form.fields['client'].queryset = Client.objects.filter(pk=client.pk)
	item_formset = OrderItemFormSet(request.POST or None)

	if request.method == 'POST' and order_form.is_valid() and item_formset.is_valid():
		with transaction.atomic():
			order = order_form.save(commit=False)
			order.status = 'pending'
			order.created_by = request.user
			order.save()
			item_formset.instance = order
			item_formset.save()
		messages.success(request, f'Order {order.order_reference} was submitted.')
		return redirect('my_orders')

	return render(request, 'orders/order_form.html', {
		'order_form': order_form,
		'item_formset': item_formset,
		'page_title': 'Place an order',
		'is_create': True,
	})
