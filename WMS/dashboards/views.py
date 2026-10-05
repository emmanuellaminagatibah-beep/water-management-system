from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Count, F, Sum
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from billing.models import Invoice, Payment
from clients.models import Client
from complaints.models import Complaint
from deliveries.models import Delivery
from deliveries.models import Driver
from Inventory.models import Inventory, StockMovement
from orders.models import Order
from products.models import Product
from accounts.decorators import role_required

from .forms import ReportFilterForm


ROLE_DASHBOARDS = {
    'admin': {
        'title': 'Operations',
        'description': 'Control the full water management operation from one place.',
        'actions': [
            ('🛡️', 'User administration', '/admin/accounts/user/', 'Create accounts and assign staff roles.'),
            ('📊', 'Admin dashboard & reports', '/dashboards/admin/', 'Review live operating totals and date-filtered reports.'),
            ('📦', 'Inventory control', '/Inventory/', 'Review stock levels, reorders, and movement history.'),
            ('📋', 'Order operations', '/orders/', 'Review, confirm, and update customer orders.'),
            ('🚚', 'Fleet dispatch', '/deliveries/', 'Review schedules and assign delivery tasks.'),
            ('💳', 'Billing & finance', '/billing/', 'Review invoices and record customer payments.'),
            ('👥', 'Client management', '/clients/manage/', 'Manage customer records and contact details.'),
            ('💧', 'Product catalog', '/products/', 'Review product availability and catalogue items.'),
            ('💬', 'Support desk', '/complaints/', 'Follow up on complaints and customer issues.'),
        ],
    },
    'sales': {
        'title': 'Sales',
        'description': 'Manage customer orders, service requests, and delivery scheduling.',
        'actions': [
            ('📋', 'Customer orders', '/orders/', 'Review and follow up on customer orders.'),
            ('🧾', 'Create order', '/orders/create/', 'Create a new order for a customer.'),
            ('👥', 'Client records', '/clients/manage/', 'Find and update customer details.'),
            ('💧', 'Water products', '/products/', 'Check products and current pricing.'),
            ('🚚', 'Dispatch planning', '/deliveries/', 'Track scheduled deliveries and routing.'),
            ('🗓️', 'Schedule delivery', '/deliveries/create/', 'Assign a driver and vehicle to an order.'),
            ('💬', 'Customer support', '/complaints/', 'Review customer issues and follow-up actions.'),
        ],
    },
    'warehouse': {
        'title': 'Warehouse',
        'description': 'Keep stock flow efficient and orders ready for dispatch.',
        'actions': [
            ('📦', 'Inventory overview', '/Inventory/', 'Review on-hand stock and low-stock items.'),
            ('🔄', 'Stock movements', '/Inventory/movements/', 'Review stock receipts and issue records.'),
            ('📋', 'Fulfilment queue', '/orders/', 'View orders that need to be prepared.'),
            ('💧', 'Product list', '/products/', 'Review products held in stock.'),
        ],
    },
    'driver': {
        'title': 'Field Operations',
        'description': 'View assigned service runs and update delivery progress on the road.',
        'actions': [
            ('🚚', 'Assigned route', '/deliveries/', 'View deliveries assigned to your driver profile.'),
            ('📍', 'Live delivery status', '/deliveries/', 'Update each route with progress and outcome notes.'),
        ],
    },
    'accounts': {
        'title': 'Finance',
        'description': 'Track billing, customer balances, and payment updates.',
        'actions': [
            ('💳', 'Invoices & payments', '/billing/', 'Review balances and record payments.'),
            ('📋', 'Order billing', '/orders/', 'Check order totals and billing references.'),
        ],
    },
    'client': {
        'title': 'Customer Portal',
        'description': 'Manage your profile, orders, and water service requests.',
        'actions': [
            ('👤', 'My account', '/clients/portal/', 'Update your contact and delivery details.'),
            ('📋', 'My orders', '/orders/my/', 'Review your order history and current status.'),
            ('🛒', 'Place order', '/orders/my/create/', 'Order available water products for your account.'),
            ('💬', 'Support requests', '/complaints/', 'Submit a complaint or review its status.'),
            ('💧', 'Product catalog', '/products/', 'Browse available water products.'),
        ],
    },
}


def home_view(request):
    return render(request, 'home.html', {
        'contact_email': settings.CONTACT_EMAIL,
        'contact_phone': settings.CONTACT_PHONE,
        'contact_location': settings.CONTACT_LOCATION,
    })


def permission_denied(request, exception=None):
    return render(request, '403.html', status=403)


def page_not_found(request, exception=None):
    return render(request, '404.html', status=404)


def server_error(request):
    return render(request, '500.html', status=500)


@login_required
def dashboard_view(request):
    if request.user.role == 'admin':
        return admin_dashboard(request)

    if request.user.role == 'client':
        client = Client.objects.filter(user=request.user).first()
        if client:
            orders = Order.objects.filter(client=client).prefetch_related('items__product')
            deliveries = Delivery.objects.filter(order__client=client).select_related('order', 'vehicle', 'driver')
            invoices = Invoice.objects.filter(client=client).select_related('order').prefetch_related('items')
            payments = Payment.objects.filter(invoice__client=client).select_related('invoice')
            complaints = Complaint.objects.filter(client=client).select_related('order', 'assigned_staff')
            products = Product.objects.filter(order_items__order__client=client).distinct()
            outstanding_balance = invoices.aggregate(total=Sum('outstanding_balance'))['total'] or 0
        else:
            orders = Order.objects.none()
            deliveries = Delivery.objects.none()
            invoices = Invoice.objects.none()
            payments = Payment.objects.none()
            complaints = Complaint.objects.none()
            products = Product.objects.none()
            outstanding_balance = 0
        return render(request, 'dashboards/client_dashboard.html', {
            'client': client,
            'orders': orders,
            'deliveries': deliveries,
            'invoices': invoices,
            'payments': payments,
            'complaints': complaints,
            'products': products,
            'outstanding_balance': outstanding_balance,
        })

    dashboard = ROLE_DASHBOARDS.get(request.user.role, ROLE_DASHBOARDS['client'])
    if request.user.role == 'sales':
        dashboard_metrics = [
            ('Pending orders', Order.objects.filter(status='pending').count()),
            ('Active clients', Client.objects.filter(status='active').count()),
            ('Deliveries underway', Delivery.objects.filter(status__in=[Delivery.Status.SCHEDULED, Delivery.Status.DISPATCHED]).count()),
        ]
    elif request.user.role == 'warehouse':
        dashboard_metrics = [
            ('Orders to confirm', Order.objects.filter(status='pending').count()),
            ('Orders to prepare', Order.objects.filter(status='confirmed').count()),
            ('Low-stock products', Inventory.objects.low_stock().count()),
        ]
    elif request.user.role == 'driver':
        driver = Driver.objects.filter(user=request.user, is_active=True).first()
        assigned_deliveries = Delivery.objects.filter(driver=driver) if driver else Delivery.objects.none()
        dashboard_metrics = [
            ('Scheduled runs', assigned_deliveries.filter(status=Delivery.Status.SCHEDULED).count()),
            ('Runs in progress', assigned_deliveries.filter(status=Delivery.Status.DISPATCHED).count()),
            ('Completed runs', assigned_deliveries.filter(status=Delivery.Status.DELIVERED).count()),
        ]
    else:
        current_date = timezone.localdate()
        dashboard_metrics = [
            ('Open invoices', Invoice.objects.filter(payment_status__in=[Invoice.PaymentStatus.UNPAID, Invoice.PaymentStatus.PARTIALLY_PAID]).count()),
            ('Outstanding balance', Invoice.objects.aggregate(total=Sum('outstanding_balance'))['total'] or 0),
            ('Payments this month', Payment.objects.filter(payment_date__year=current_date.year, payment_date__month=current_date.month).aggregate(total=Sum('amount'))['total'] or 0),
        ]
    return render(request, 'dashboards/dashboard.html', {
        'dashboard_title': dashboard['title'],
        'dashboard_description': dashboard['description'],
        'dashboard_actions': dashboard['actions'],
        'dashboard_metrics': dashboard_metrics,
    })


@login_required
@role_required('admin')
def admin_dashboard(request):
    context = {
        'total_clients': Client.objects.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'deliveries_awaiting': Delivery.objects.filter(
            status__in=[Delivery.Status.SCHEDULED, Delivery.Status.DISPATCHED, Delivery.Status.PARTIALLY_DELIVERED],
        ).count(),
        'available_products': Inventory.objects.filter(quantity__gt=F('reserved_quantity')).count(),
        'low_stock_products': Inventory.objects.filter(quantity__lte=F('reorder_level')).count(),
        'outstanding_total': Invoice.objects.aggregate(total=Sum('outstanding_balance'))['total'] or 0,
        'recent_payments': Payment.objects.select_related('invoice', 'invoice__client', 'received_by').order_by('-payment_date', '-paid_at')[:10],
        'open_complaints': Complaint.objects.filter(status__in=[Complaint.Status.OPEN, Complaint.Status.IN_PROGRESS]).count(),
    }
    return render(request, 'dashboards/admin_dashboard.html', context)


@login_required
@role_required('admin')
def report_view(request, report_type):
    if report_type not in {'sales', 'inventory', 'orders', 'deliveries', 'payments'}:
        from django.http import Http404
        raise Http404('Report not found.')

    form = ReportFilterForm(request.GET or None)
    rows = []
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        if start_date and end_date and start_date > end_date:
            form.add_error('end_date', 'End date must be on or after the start date.')
        else:
            if report_type == 'sales':
                rows = Invoice.objects.select_related('client', 'order').annotate(
                    payment_count=Count('payments'),
                    amount_collected=Sum('payments__amount'),
                ).order_by('-issue_date')
                rows = _date_range(rows, 'issue_date', start_date, end_date)
            elif report_type == 'inventory':
                rows = StockMovement.objects.select_related('product', 'created_by').order_by('-created_at')
                rows = _date_range(rows, 'created_at__date', start_date, end_date)
            elif report_type == 'orders':
                rows = Order.objects.select_related('client', 'created_by').prefetch_related('items__product').annotate(
                    item_count=Count('items'),
                    item_quantity=Sum('items__quantity'),
                ).order_by('-created_at')
                rows = _date_range(rows, 'created_at__date', start_date, end_date)
            elif report_type == 'deliveries':
                rows = Delivery.objects.select_related('order__client', 'vehicle', 'driver').order_by('-scheduled_date')
                rows = _date_range(rows, 'scheduled_date__date', start_date, end_date)
            else:
                rows = Payment.objects.select_related('invoice__client', 'invoice', 'received_by').order_by('-payment_date', '-paid_at')
                rows = _date_range(rows, 'payment_date', start_date, end_date)

    return render(request, 'dashboards/report_list.html', {
        'report_type': report_type,
        'report_title': report_type.title(),
        'form': form,
        'rows': rows,
    })


def _date_range(queryset, field, start_date, end_date):
    if start_date:
        queryset = queryset.filter(**{f'{field}__gte': start_date})
    if end_date:
        queryset = queryset.filter(**{f'{field}__lte': end_date})
    return queryset
