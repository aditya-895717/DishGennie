"""
Serves media stored in the database at MEDIA_URL.

Replaces django.conf.urls.static's DEBUG-only file server, which could never
have worked on Vercel's read-only filesystem.
"""
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_safe

from .models import StoredFile
from .storage import _as_bytes

# KYC uploads. Unlike a QR code or an avatar, these must not be readable by
# anyone who guesses the URL — only the admin reviewing them and the maid
# who submitted them.
PRIVATE_PREFIXES = ('documents/',)


def _is_private(name):
    return name.startswith(PRIVATE_PREFIXES)


def _may_read_private(user, name):
    if not user.is_authenticated:
        return False
    if user.is_admin_user:
        return True
    profile = getattr(user, 'maid_profile', None)
    if profile is None:
        return False
    return type(profile).objects.filter(
        Q(pk=profile.pk),
        Q(aadhaar_document=name) | Q(police_verification=name) | Q(id_proof=name),
    ).exists()


@require_safe
@cache_control(private=True, max_age=3600)
def serve_media(request, path):
    name = path.lstrip('/')

    if _is_private(name) and not _may_read_private(request.user, name):
        return HttpResponseForbidden('You do not have access to this document.')

    try:
        record = StoredFile.objects.get(name=name)
    except StoredFile.DoesNotExist:
        raise Http404(f'No stored file named {name!r}')

    response = FileResponse(
        iter([_as_bytes(record.content)]),
        content_type=record.content_type or 'application/octet-stream',
    )
    response['Content-Length'] = record.size
    return response
