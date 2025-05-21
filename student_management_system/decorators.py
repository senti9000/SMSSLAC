from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

def admin_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a superuser (admin),
    redirects to login page if necessary.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def student_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a student (not staff or superuser),
    redirects to login page if necessary.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_superuser or getattr(request.user, 'is_staff_member', False):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def staff_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a staff member (not superuser),
    redirects to login page if necessary.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_superuser or not getattr(request.user, 'is_staff_member', False):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view
