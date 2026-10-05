from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from orders.models import Order

from .forms import InvoiceCreateForm, PaymentForm
from .models import Invoice, Payment
from .services.invoices import generate_invoice
from .services.payments import record_payment


@login_required
@role_required('admin', 'accounts', 'client')
def invoice_list(request):
	invoices = Invoice.objects.select_related('order', 'client').prefetch_related('payments', 'items')
	if request.user.role == 'client':
		invoices = invoices.filter(client__user=request.user)
	return render(request, 'billing/invoice_list.html', {'invoices': invoices})


@login_required
@role_required('admin', 'accounts')
def invoice_create(request):
	form = InvoiceCreateForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		order = form.cleaned_data['order']
		try:
			invoice = generate_invoice(order, form.cleaned_data['due_date'], request.user)
		except ValidationError as error:
			form.add_error(None, error)
		else:
			messages.success(request, f'Invoice {invoice.invoice_number} was issued.')
			return redirect('invoice_detail', invoice_id=invoice.pk)
	return render(request, 'billing/invoice_form.html', {'form': form})


@login_required
@role_required('admin', 'accounts', 'client')
def invoice_detail(request, invoice_id):
	invoices = Invoice.objects.select_related('order', 'client').prefetch_related('items', 'payments')
	if request.user.role == 'client':
		invoices = invoices.filter(client__user=request.user)
	invoice = get_object_or_404(invoices, pk=invoice_id)
	return render(request, 'billing/invoice_detail.html', {'invoice': invoice})


@login_required
@role_required('admin', 'accounts', 'client')
def invoice_print(request, invoice_id):
	invoices = Invoice.objects.select_related('order', 'client').prefetch_related('items')
	if request.user.role == 'client':
		invoices = invoices.filter(client__user=request.user)
	invoice = get_object_or_404(invoices, pk=invoice_id)
	return render(request, 'billing/invoice_print.html', {'invoice': invoice})


@login_required
@role_required('admin', 'accounts')
def payment_create(request, invoice_id):
	invoice = get_object_or_404(Invoice, pk=invoice_id)
	form = PaymentForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		try:
			payment = record_payment(
				invoice=invoice,
				amount=form.cleaned_data['amount'],
				method=form.cleaned_data['method'],
				reference=form.cleaned_data['reference'],
				acting_user=request.user,
			)
		except ValidationError as error:
			form.add_error(None, error)
		else:
			messages.success(request, f'Payment recorded for {invoice.invoice_number}.')
			return redirect('payment_history', invoice_id=invoice.pk)
	return render(request, 'billing/payment_form.html', {'form': form, 'invoice': invoice})


@login_required
@role_required('admin', 'accounts')
def payment_list(request):
	payments = Payment.objects.select_related('invoice', 'invoice__client', 'received_by')
	return render(request, 'billing/payment_list.html', {'payments': payments})


@login_required
@role_required('admin', 'accounts', 'client')
def payment_history(request, invoice_id):
	invoices = Invoice.objects.select_related('client', 'order').prefetch_related('payments__received_by')
	if request.user.role == 'client':
		invoices = invoices.filter(client__user=request.user)
	invoice = get_object_or_404(invoices, pk=invoice_id)
	return render(request, 'billing/payment_history.html', {
		'invoice': invoice,
		'payments': invoice.payments.select_related('received_by').order_by('-payment_date', '-paid_at'),
	})
