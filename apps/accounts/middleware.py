"""
Custom middleware for DishGennie.
"""
from django.utils.cache import add_never_cache_headers


class NoCacheAfterLogoutMiddleware:
    """
    Prevents the browser back button from showing cached authenticated pages
    after the user has logged out. Adds no-cache headers to all authenticated
    page responses.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Add no-cache headers to all authenticated views
        # This prevents browser back button from showing stale dashboard pages
        if request.user.is_authenticated:
            add_never_cache_headers(response)

        # Also add for login/logout pages to prevent caching those
        if request.path.startswith('/accounts/'):
            add_never_cache_headers(response)

        return response
