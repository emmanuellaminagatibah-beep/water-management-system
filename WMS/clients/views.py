import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.decorators import role_required

from .forms import ClientCreateForm, ClientProfileForm
from .models import Client


@login_required
@role_required('client')
def client_portal(request):
	client = Client.objects.filter(user=request.user).first()
	form = ClientProfileForm(request.POST or None, instance=client)
	if request.method == 'POST' and form.is_valid():
		client = form.save(commit=False)
		client.user = request.user
		if not client.client_id:
			client.client_id = f'WEB-{uuid.uuid4().hex[:10].upper()}'
		client.save()
		messages.success(request, 'Your account details have been saved.')
		return redirect('client_portal')
	return render(request, 'clients/client_portal.html', {'form': form, 'client': client})


@login_required
@role_required('admin', 'sales', 'accounts')
def client_list(request):
	clients = Client.objects.order_by('client_id')
	return render(request, 'clients/client_list.html', {'clients': clients})


@login_required
@role_required('admin', 'sales')
def client_create(request):
	form = ClientCreateForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Client created successfully.')
		return redirect('client_list')
	return render(request, 'clients/client_form.html', {'form': form})
