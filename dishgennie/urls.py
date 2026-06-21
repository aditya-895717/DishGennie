"""
URL configuration for DishGennie project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import datetime
import os
import pathlib
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render


def ping(request):
    return JsonResponse({
        "status": "ok",
        "service": "DishGennie",
        "timestamp": str(datetime.datetime.now()),
        "email_configured": bool(os.environ.get("BREVO_SMTP_KEY")),
    })


def service_worker(request):
    """Serve sw.js from /sw.js (root scope) with required Service-Worker-Allowed header."""
    sw_path = pathlib.Path(settings.BASE_DIR) / 'static' / 'js' / 'sw.js'
    content = sw_path.read_text(encoding='utf-8')
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


def offline(request):
    return render(request, 'offline.html')


urlpatterns = [
    # Keep-alive endpoint (pinged every 5 min to prevent Render free-tier sleep)
    path('ping/', ping, name='ping'),

    # PWA — must be at root scope, not under /static/
    path('sw.js', service_worker, name='service-worker'),
    path('offline.html', offline, name='offline'),

    # Django Admin
    path('django-admin/', admin.site.urls),

    # API endpoints
    path('api/v1/accounts/', include('apps.accounts.api_urls')),
    path('api/v1/services/', include('apps.services.urls')),
    path('api/v1/bookings/', include('apps.bookings.api_urls')),
    path('api/v1/payments/', include('apps.payments.api_urls')),
    path('api/v1/reviews/', include('apps.reviews.api_urls')),
    path('api/v1/notifications/', include('apps.notifications.api_urls')),
    path('api/v1/tracking/', include('apps.tracking.api_urls')),
    path('api/v1/support/', include('apps.support.api_urls')),
    path('api/v1/admin-panel/', include('apps.analytics.api_urls')),

    # Template views (pages)
    path('', include('apps.accounts.urls')),
    path('bookings/', include('apps.bookings.urls')),
    path('payments/', include('apps.payments.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'
