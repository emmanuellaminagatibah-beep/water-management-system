"""
URL configuration for WMS project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from dashboards import views as dashboard_views

admin.site.site_header = 'Water Management System'
admin.site.site_title = 'Water Management System'
admin.site.index_title = 'Operations Dashboard'

urlpatterns = [
    path('', dashboard_views.home_view, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
path('clients/', include('clients.urls')),
    path('products/', include('products.urls')),
    path('Inventory/', include('Inventory.urls')),
    path('orders/', include('orders.urls')),
    path('deliveries/', include('deliveries.urls')),
    path('billing/', include('billing.urls')),
    path('complaints/', include('complaints.urls')),
    path('dashboards/', include('dashboards.urls')),
    



]

handler403 = 'dashboards.views.permission_denied'
handler404 = 'dashboards.views.page_not_found'
handler500 = 'dashboards.views.server_error'
