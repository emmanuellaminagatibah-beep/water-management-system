from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def role_required(*allowed_roles):
	def decorator(view_func):
		@wraps(view_func)
		def wrapped_view(request, *args, **kwargs):
			if not request.user.is_authenticated:
				return redirect_to_login(request.get_full_path())
			if request.user.is_superuser or request.user.role in allowed_roles:
				return view_func(request, *args, **kwargs)
			raise PermissionDenied

		return wrapped_view

	return decorator