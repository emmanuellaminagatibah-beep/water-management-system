from django.urls import path

from . import views

urlpatterns = [
	path('portal/', views.client_portal, name='client_portal'),
	path('manage/', views.client_list, name='client_list'),
	path('manage/create/', views.client_create, name='client_create'),
]