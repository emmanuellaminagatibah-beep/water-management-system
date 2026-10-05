from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from clients.models import Client

from .forms import ComplaintCreateForm, ComplaintUpdateForm
from .models import Complaint
from .services import update_complaint


@login_required
@role_required('admin', 'sales', 'client')
def complaint_list(request):
	client = get_object_or_404(Client, user=request.user) if request.user.role == 'client' else None
	complaints = Complaint.objects.select_related('client', 'order', 'assigned_staff')
	if request.user.role == 'client':
		complaints = complaints.filter(client=client)
		form = ComplaintCreateForm(request.POST or None, client=client)
		if request.method == 'POST' and form.is_valid():
			complaint = form.save(commit=False)
			complaint.client = client
			complaint.save()
			messages.success(request, 'Your complaint has been submitted.')
			return redirect('complaint_list')
	else:
		form = None
	return render(request, 'complaints/complaint_list.html', {
		'complaints': complaints,
		'form': form,
		'client': client,
	})


@login_required
@role_required('admin', 'sales')
def complaint_update(request, pk):
	complaint = get_object_or_404(Complaint.objects.select_related('client', 'order', 'assigned_staff'), pk=pk)
	form = ComplaintUpdateForm(request.POST or None, instance=complaint)
	if request.method == 'POST' and form.is_valid():
		try:
			update_complaint(
				complaint=complaint,
				new_status=form.cleaned_data['status'],
				assigned_staff=form.cleaned_data['assigned_staff'],
				staff_response=form.cleaned_data['staff_response'],
				acting_user=request.user,
			)
		except ValidationError as error:
			form.add_error(None, error)
		else:
			messages.success(request, 'Complaint updated.')
			return redirect('complaint_list')
	return render(request, 'complaints/complaint_update.html', {'form': form, 'complaint': complaint})
