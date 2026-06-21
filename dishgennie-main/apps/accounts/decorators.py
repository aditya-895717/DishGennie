"""
Reusable decorators for role-based template view access.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def role_required(*roles):
    """
    Decorator that ensures the logged-in user has one of the allowed roles.
    Redirects to the user's correct dashboard if they don't.
    Usage: @role_required('customer')  or  @role_required('maid', 'admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if (
                request.user.role in roles
                or ('admin' in roles and request.user.is_admin_user)
                or ('maid' in roles and request.user.is_maid_user)
                or ('customer' in roles and request.user.is_customer_user and not request.user.is_admin_user)
            ):
                return view_func(request, *args, **kwargs)
            return _redirect_by_role(request.user)
        return wrapper
    return decorator


def customer_required(view_func):
    """Shortcut: only customers can access."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_customer_user and not request.user.is_admin_user:
            return view_func(request, *args, **kwargs)
        return _redirect_by_role(request.user)
    return wrapper


def maid_required(view_func):
    """Shortcut: only maids can access."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_maid_user:
            return view_func(request, *args, **kwargs)
        return _redirect_by_role(request.user)
    return wrapper


def admin_required(view_func):
    """Shortcut: only admins can access."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_admin_user:
            return view_func(request, *args, **kwargs)
        return _redirect_by_role(request.user)
    return wrapper


def _redirect_by_role(user):
    """Redirect user to their role-based dashboard."""
    if user.is_admin_user:
        return redirect('admin-dashboard')
    elif user.is_maid_user:
        return redirect('maid-dashboard')
    return redirect('user-dashboard')
