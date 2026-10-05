from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from deliveries.models import Delivery
from orders.models import Order

VALID_TRANSITIONS = {
	Delivery.Status.SCHEDULED: {
		Delivery.Status.DISPATCHED,
		Delivery.Status.CANCELLED,
	},
	Delivery.Status.DISPATCHED: {
		Delivery.Status.DELIVERED,
		Delivery.Status.PARTIALLY_DELIVERED,
		Delivery.Status.FAILED,
		Delivery.Status.CANCELLED,
	},
	Delivery.Status.DELIVERED: set(),
	Delivery.Status.PARTIALLY_DELIVERED: set(),
	Delivery.Status.FAILED: set(),
	Delivery.Status.CANCELLED: set(),
}


@transaction.atomic
def schedule_delivery(order, driver, vehicle, destination, scheduled_date, status=None):
	delivery = Delivery(
		order=order,
		driver=driver,
		vehicle=vehicle,
		destination=destination,
		scheduled_date=scheduled_date,
		status=status or Delivery.Status.SCHEDULED,
	)
	delivery.full_clean()
	delivery.save()
	return delivery


@transaction.atomic
def change_delivery_status(*, delivery, new_status, acting_user, status_note=''):
	delivery = Delivery.objects.select_for_update().select_related('order', 'driver__user', 'vehicle').get(pk=delivery.pk)
	current_status = delivery.status
	status_note = (status_note or '').strip()
	if new_status not in Delivery.Status.values:
		raise ValidationError('The selected delivery status is invalid.')
	if new_status not in VALID_TRANSITIONS.get(current_status, set()):
		raise ValidationError(f'A delivery cannot move from {current_status} to {new_status}.')

	is_admin = acting_user.is_superuser or acting_user.role == User.Role.ADMIN
	is_sales = acting_user.role == User.Role.SALES
	is_assigned_driver = (
		acting_user.role == User.Role.DRIVER
		and hasattr(acting_user, 'driver_profile')
		and delivery.driver_id == acting_user.driver_profile.id
	)

	if is_admin:
		pass
	elif is_sales:
		allowed_sales_changes = {Delivery.Status.DISPATCHED, Delivery.Status.CANCELLED}
		if current_status != Delivery.Status.SCHEDULED or new_status not in allowed_sales_changes:
			raise PermissionDenied('Sales staff can only dispatch or cancel scheduled deliveries.')
	elif is_assigned_driver:
		allowed_driver_changes = {
			Delivery.Status.DELIVERED,
			Delivery.Status.PARTIALLY_DELIVERED,
			Delivery.Status.FAILED,
		}
		if current_status != Delivery.Status.DISPATCHED or new_status not in allowed_driver_changes:
			raise PermissionDenied('Drivers can update only their own dispatched deliveries.')
	else:
		raise PermissionDenied('You do not have permission to update this delivery.')

	if new_status == Delivery.Status.DISPATCHED:
		delivery.full_clean()
		delivery.dispatched_at = timezone.now()

	completed_statuses = {
		Delivery.Status.DELIVERED,
		Delivery.Status.PARTIALLY_DELIVERED,
		Delivery.Status.FAILED,
		Delivery.Status.CANCELLED,
	}
	if new_status in completed_statuses:
		delivery.completed_at = timezone.now()
		if new_status in {Delivery.Status.DELIVERED, Delivery.Status.FAILED, Delivery.Status.CANCELLED}:
			delivery.delivered_at = timezone.now()

	delivery.status = new_status
	if status_note:
		delivery.status_note = status_note
	delivery.save()
	if new_status == Delivery.Status.PARTIALLY_DELIVERED:
		Order.objects.filter(pk=delivery.order_id).update(status='partially_delivered')
	elif new_status == Delivery.Status.DELIVERED:
		open_deliveries = Delivery.objects.filter(order_id=delivery.order_id).exclude(
			status__in=[Delivery.Status.DELIVERED, Delivery.Status.PARTIALLY_DELIVERED, Delivery.Status.CANCELLED],
		).exists()
		if not open_deliveries:
			has_partial_delivery = Delivery.objects.filter(
				order_id=delivery.order_id,
				status=Delivery.Status.PARTIALLY_DELIVERED,
			).exists()
			Order.objects.filter(pk=delivery.order_id).update(
				status='partially_delivered' if has_partial_delivery else 'delivered',
			)
	return delivery