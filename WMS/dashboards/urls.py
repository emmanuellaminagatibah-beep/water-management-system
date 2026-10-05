from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('reports/<str:report_type>/', views.report_view, name='report_list'),
]
