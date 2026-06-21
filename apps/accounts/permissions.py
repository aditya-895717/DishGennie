"""
Role-based permission classes for DishGennie.
"""
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow access only to admin users."""
    message = 'Admin access required.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_admin_user
        )


class IsMaid(BasePermission):
    """Allow access only to verified maid users."""
    message = 'Maid access required.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_maid_user
        )


class IsCustomer(BasePermission):
    """Allow access only to customer users."""
    message = 'Customer access required.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_customer_user
            and not request.user.is_admin_user
        )


class IsOwnerOrAdmin(BasePermission):
    """Allow access to object owners or admins."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_user:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'customer'):
            return obj.customer == request.user
        if hasattr(obj, 'maid'):
            return obj.maid == request.user
        return obj == request.user


class IsMaidOrAdmin(BasePermission):
    """Allow access to maid or admin users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_maid_user or request.user.is_admin_user)
        )
