from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = (
		'sku',
		'name',
		'category',
		'package_size',
		'unit_price',
		'reorder_level',
		'is_active',
	)
	search_fields = ('sku', 'name', 'category', 'package_size')
	list_filter = ('category', 'package_size', 'is_active')
