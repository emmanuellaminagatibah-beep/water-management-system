from django.contrib import admin

from .models import Inventory, StockMovement


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
	list_display = ('product', 'quantity', 'reorder_level', 'available_quantity', 'is_low_stock', 'location', 'updated_at')
	search_fields = ('product__sku', 'product__name', 'location')
	list_filter = ('product',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
	list_display = ('product', 'movement_type', 'quantity', 'reference', 'created_by', 'created_at')
	search_fields = ('product__sku', 'reference')
	list_filter = ('movement_type', 'created_at')
	readonly_fields = ('created_at',)
