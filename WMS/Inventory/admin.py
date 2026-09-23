from django.contrib import admin

from .models import Inventory, StockMovement


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
	list_display = ('product', 'quantity', 'reserved_quantity', 'available_quantity', 'location', 'updated_at')
	search_fields = ('product__sku', 'product__name', 'location')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
	list_display = ('product', 'movement_type', 'quantity', 'reference', 'created_by', 'created_at')
	search_fields = ('product__sku', 'reference')
	list_filter = ('movement_type', 'created_at')
