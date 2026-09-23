from django.contrib import admin

from .models import Invoice, Payment


class PaymentInline(admin.TabularInline):
	model = Payment
	extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
	list_display = ('invoice_number', 'order', 'total', 'status', 'due_date', 'issued_at')
	search_fields = ('invoice_number', 'order__client__name')
	list_filter = ('status', 'due_date')
	inlines = (PaymentInline,)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = ('invoice', 'amount', 'method', 'reference', 'paid_at')
	search_fields = ('invoice__invoice_number', 'reference')
	list_filter = ('method', 'paid_at')
