from django.urls import path
from . import views

urlpatterns = [
	path('', views.complaint_list, name='complaint_list'),
	path('<int:pk>/update/', views.complaint_update, name='complaint_update'),
]
