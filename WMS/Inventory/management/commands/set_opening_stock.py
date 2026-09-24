from django.core.management.base import BaseCommand

from products.models import Product

from Inventory.models import Inventory, StockMovement
from Inventory.services import adjust_stock


class Command(BaseCommand):
	help = 'Set opening stock for a product'

	def add_arguments(self, parser):
		parser.add_argument('product_id', type=int)
		parser.add_argument('quantity', type=int)

	def handle(self, *args, **options):
		product = Product.objects.get(pk=options['product_id'])
		Inventory.objects.get_or_create(product=product)
		adjust_stock(
			product,
			options['quantity'],
			StockMovement.MovementType.OPENING,
			note='Initial opening stock',
		)
		self.stdout.write(self.style.SUCCESS(f'Set opening stock for {product}'))