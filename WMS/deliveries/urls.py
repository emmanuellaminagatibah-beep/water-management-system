from django.urls import path
from deliveries import views

urlpatterns = [
	path('', views.delivery_list, name='delivery_list'),
	path('create/', views.delivery_create, name='delivery_create'),
]
