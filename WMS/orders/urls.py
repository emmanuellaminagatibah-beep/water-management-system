from django.urls import path
from orders import views

urlpatterns = [
	path('', views.order_list, name='orders'),
	path('create/', views.order_create, name='order_create'),
	path('<int:pk>/', views.order_detail, name='order_detail'),
	path('<int:pk>/edit/', views.order_edit, name='order_edit'),
]