from django.urls import path
from billing import views

urlpatterns = [
	path('', views.invoice_list, name='invoice_list'),
	path('create/', views.invoice_create, name='invoice_create'),
	path('payments/', views.payment_list, name='payment_list'),
	path('<int:invoice_id>/payments/', views.payment_create, name='payment_create'),
	path('<int:invoice_id>/payments/history/', views.payment_history, name='payment_history'),
	path('<int:invoice_id>/print/', views.invoice_print, name='invoice_print'),
	path('<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
]