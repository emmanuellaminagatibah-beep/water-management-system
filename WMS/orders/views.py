from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OrderCreateForm, OrderEditForm, OrderItemFormSet
from .models import Order


staff_required = user_passes_test(lambda user: user.is_staff or user.is_superuser)


@login_required
@staff_required
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
@staff_required
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
@staff_required
def order_edit(request, pk):
	order = get_object_or_404(Order.objects.select_related('client'), pk=pk)
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
@staff_required
def order_detail(request, pk):
	order = get_object_or_404(
		Order.objects.select_related('client').prefetch_related('items__product'),
		pk=pk,
	)
	return render(request, 'orders/order_detail.html', {'order': order})
