from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User

from .models import Complaint


VALID_TRANSITIONS = {
	Complaint.Status.OPEN: {Complaint.Status.IN_PROGRESS},
	Complaint.Status.IN_PROGRESS: {Complaint.Status.RESOLVED},
	Complaint.Status.RESOLVED: {Complaint.Status.CLOSED},
	Complaint.Status.CLOSED: set(),
}


@transaction.atomic
def update_complaint(*, complaint, new_status, assigned_staff, staff_response, acting_user):
	if not (acting_user.is_superuser or acting_user.role in {User.Role.ADMIN, User.Role.SALES}):
		raise PermissionDenied('Only administrators and sales staff can update complaints.')

	new_status = str(new_status).upper()
	if new_status not in Complaint.Status.values:
		raise ValidationError('Choose a valid complaint status.')
	if assigned_staff and assigned_staff.role not in {User.Role.ADMIN, User.Role.SALES}:
		raise ValidationError({'assigned_to': 'Complaints can only be assigned to administrators or sales staff.'})

	locked_complaint = Complaint.objects.select_for_update().get(pk=complaint.pk)
	if new_status != locked_complaint.status and new_status not in VALID_TRANSITIONS[locked_complaint.status]:
		raise ValidationError(
			f'A complaint cannot move from {locked_complaint.get_status_display()} to '
			f'{dict(Complaint.Status.choices)[new_status]}.'
		)

	locked_complaint.status = new_status
	locked_complaint.assigned_staff = assigned_staff
	locked_complaint.staff_response = (staff_response or '').strip()
	if new_status == Complaint.Status.RESOLVED and not locked_complaint.resolved_date:
		locked_complaint.resolved_date = timezone.localdate()
		locked_complaint.resolved_at = timezone.now()
	locked_complaint.save(update_fields=[
		'status', 'assigned_staff', 'staff_response', 'resolved_date', 'resolved_at',
	])
	return locked_complaint