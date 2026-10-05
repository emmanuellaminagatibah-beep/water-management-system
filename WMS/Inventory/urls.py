from django.urls import path
from Inventory import views

urlpatterns = [
	path('', views.inventory_list, name='inventory-list'),
	path('movements/create/', views.stock_movement_create, name='stock-movement-create'),
	path('movements/', views.stock_movement_history, name='stock-movement-history'),
]
