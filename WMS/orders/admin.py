from django.contrib import admin

from .forms import OrderItemForm
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	form = OrderItemForm
	fields = ('product', 'quantity', 'unit_price', 'subtotal')
	readonly_fields = ('unit_price', 'subtotal')
	min_num = 1
	validate_min = True
	extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('order_reference', 'client', 'total_amount', 'status', 'created_at')
	search_fields = ('order_reference', 'client__client_id', 'client__business_name', 'client__phone')
	list_filter = ('status', 'created_at')
	inlines = (OrderItemInline,)
	readonly_fields = ('order_reference', 'total_amount', 'created_at', 'updated_at')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
	list_display = ('order', 'product', 'quantity', 'unit_price', 'subtotal')
	search_fields = ('order__order_reference', 'order__client__client_id', 'order__client__business_name', 'product__sku', 'product__name')
	readonly_fields = ('unit_price', 'subtotal')

	def save_model(self, request, obj, form, change):
		if not change or 'product' in form.changed_data:
			obj.unit_price = obj.product.unit_price
		super().save_model(request, obj, form, change)
