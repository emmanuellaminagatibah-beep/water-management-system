from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('id', 'client', 'status', 'total_amount', 'created_by', 'created_at')
	search_fields = ('client__name',)
	list_filter = ('status', 'created_at')
	inlines = (OrderItemInline,)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
	list_display = ('order', 'product', 'quantity', 'unit_price', 'line_total')
	search_fields = ('order__client__name', 'product__sku', 'product__name')
