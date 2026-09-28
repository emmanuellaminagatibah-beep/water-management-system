from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError

from .forms import OrderItemForm
from .models import Order, OrderItem
from .services import cancel_order, confirm_order


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	form = OrderItemForm
	fields = ('product', 'quantity', 'unit_price', 'subtotal')
	readonly_fields = ('unit_price', 'subtotal')
	min_num = 1
	validate_min = True
	extra = 0

	def has_add_permission(self, request, obj=None):
		return (obj is None or obj.status == 'pending') and super().has_add_permission(request, obj)

	def has_change_permission(self, request, obj=None):
		return (obj is None or obj.status == 'pending') and super().has_change_permission(request, obj)

	def has_delete_permission(self, request, obj=None):
		return (obj is not None and obj.status == 'pending') and super().has_delete_permission(request, obj)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('order_reference', 'client', 'total_amount', 'status', 'created_at')
	search_fields = ('order_reference', 'client__client_id', 'client__business_name', 'client__phone')
	list_filter = ('status', 'created_at')
	inlines = (OrderItemInline,)
	readonly_fields = ('order_reference', 'total_amount', 'created_at', 'updated_at', 'status')
	actions = ('confirm_selected_orders', 'cancel_selected_orders')

	def has_delete_permission(self, request, obj=None):
		return (obj is None or obj.status == 'pending') and super().has_delete_permission(request, obj)

	def get_actions(self, request):
		actions = super().get_actions(request)
		actions.pop('delete_selected', None)
		return actions

	def delete_queryset(self, request, queryset):
		if queryset.exclude(status='pending').exists():
			raise PermissionDenied('Only pending orders can be deleted.')
		super().delete_queryset(request, queryset)

	@admin.action(description='Confirm selected pending orders')
	def confirm_selected_orders(self, request, queryset):
		self._run_order_action(request, queryset, confirm_order, 'confirmed')

	@admin.action(description='Cancel selected confirmed orders')
	def cancel_selected_orders(self, request, queryset):
		self._run_order_action(request, queryset, cancel_order, 'cancelled')

	def _run_order_action(self, request, queryset, service, success_status):
		for order in queryset:
			try:
				service(order, user=request.user)
			except ValidationError as error:
				self.message_user(request, f'{order.order_reference}: {error.messages[0]}', level=messages.ERROR)
			else:
				self.message_user(request, f'{order.order_reference} {success_status} successfully.')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
	list_display = ('order', 'product', 'quantity', 'unit_price', 'subtotal')
	search_fields = ('order__order_reference', 'order__client__client_id', 'order__client__business_name', 'product__sku', 'product__name')
	readonly_fields = ('unit_price', 'subtotal')

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return (obj is None or obj.order.status == 'pending') and super().has_change_permission(request, obj)

	def has_delete_permission(self, request, obj=None):
		return (obj is not None and obj.order.status == 'pending') and super().has_delete_permission(request, obj)

	def save_model(self, request, obj, form, change):
		if obj.order.status != 'pending':
			raise PermissionDenied('Items on confirmed orders cannot be changed.')
		if not change or 'product' in form.changed_data:
			obj.unit_price = obj.product.unit_price
		super().save_model(request, obj, form, change)
