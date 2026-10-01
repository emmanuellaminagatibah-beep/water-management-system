from django.urls import path
from deliveries import views

urlpatterns = [
	path('driver/deliveries/', views.driver_delivery_list, name='driver-delivery-list'),
	path('driver/deliveries/<int:pk>/update/', views.driver_delivery_update, name='driver-delivery-update'),
	path('client/deliveries/', views.client_delivery_list, name='client-delivery-list'),
	path('<int:pk>/status/', views.delivery_update_status, name='delivery_update_status'),
	path('<int:pk>/update/', views.staff_delivery_update, name='staff-delivery-update'),
	path('', views.delivery_list, name='delivery_list'),
	path('create/', views.delivery_create, name='delivery_create'),
]
