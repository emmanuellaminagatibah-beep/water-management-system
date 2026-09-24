from django.urls import path
from Inventory import views

urlpatterns = [
	path('', views.inventory_list, name='inventory-list'),
	path('movements/', views.stock_movement_history, name='stock-movement-history'),
]
