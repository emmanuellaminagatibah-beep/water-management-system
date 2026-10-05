from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.decorators import role_required

from .models import Product


@login_required
@role_required('admin', 'sales', 'warehouse', 'accounts', 'client')
def product_catalog(request):
	products = Product.objects.filter(is_active=True).order_by('name')
	return render(request, 'products/product_catalog.html', {'products': products})
