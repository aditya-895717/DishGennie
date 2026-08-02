"""
A Django Storage backend that keeps uploaded files in the database.

Wired in as STORAGES['default'] so every FileField/ImageField in the project
(MaidProfile.qr_code, MaidProfile.aadhaar_document, CustomUser.avatar, ...)
transparently reads and writes Neon Postgres instead of the local disk.

Files are served back by apps.filestore.views.serve_media, mounted at
MEDIA_URL, so the existing `.url` templates and serializers keep working
without change.
"""
import mimetypes
import posixpath

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri

# Guards the bytea column against someone uploading a video as an "ID proof".
DEFAULT_MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


def max_upload_bytes():
    return getattr(settings, 'FILESTORE_MAX_UPLOAD_BYTES', DEFAULT_MAX_UPLOAD_BYTES)


def _as_bytes(value):
    """Postgres hands bytea back as memoryview, SQLite as bytes."""
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, str):
        return value.encode()
    return bytes(value or b'')


@deconstructible
class DatabaseStorage(Storage):
    """Stores file contents in the filestore.StoredFile table."""

    def _model(self):
        # Imported lazily — the storage is instantiated while apps load.
        from .models import StoredFile
        return StoredFile

    # ─── Django Storage API ───────────────────────────────────────────

    def _normalize(self, name):
        name = str(name).replace('\\', '/').lstrip('/')
        if not name or '..' in name.split('/'):
            raise SuspiciousFileOperation(f'Refusing to store file at {name!r}')
        return name

    def _open(self, name, mode='rb'):
        if 'w' in mode:
            raise ValueError('DatabaseStorage files are read-only; use save() to write.')
        name = self._normalize(name)
        try:
            record = self._model().objects.get(name=name)
        except self._model().DoesNotExist:
            raise FileNotFoundError(name)
        return ContentFile(_as_bytes(record.content), name=name)

    def _save(self, name, content):
        name = self._normalize(name)
        content.seek(0)
        data = content.read()
        if isinstance(data, str):
            data = data.encode()

        limit = max_upload_bytes()
        if len(data) > limit:
            raise SuspiciousFileOperation(
                f'File is {len(data)} bytes, which exceeds the {limit} byte upload limit.'
            )

        content_type = (
            getattr(content, 'content_type', None)
            or mimetypes.guess_type(name)[0]
            or 'application/octet-stream'
        )

        self._model().objects.update_or_create(
            name=name,
            defaults={'content': data, 'content_type': content_type, 'size': len(data)},
        )
        return name

    def delete(self, name):
        self._model().objects.filter(name=self._normalize(name)).delete()

    def exists(self, name):
        try:
            normalized = self._normalize(name)
        except SuspiciousFileOperation:
            return False
        return self._model().objects.filter(name=normalized).exists()

    def size(self, name):
        try:
            return self._model().objects.values_list('size', flat=True).get(name=self._normalize(name))
        except self._model().DoesNotExist:
            raise FileNotFoundError(name)

    def url(self, name):
        media_url = getattr(settings, 'MEDIA_URL', '/media/') or '/media/'
        return f"{media_url.rstrip('/')}/{filepath_to_uri(self._normalize(name))}"

    def listdir(self, path):
        path = self._normalize(path) if path else ''
        prefix = f'{path}/' if path else ''
        directories, files = set(), []
        names = self._model().objects.filter(name__startswith=prefix).values_list('name', flat=True)
        for name in names:
            remainder = name[len(prefix):]
            head, _, tail = remainder.partition('/')
            if tail:
                directories.add(head)
            else:
                files.append(head)
        return sorted(directories), sorted(files)

    def get_created_time(self, name):
        try:
            return self._model().objects.values_list('created_at', flat=True).get(
                name=self._normalize(name)
            )
        except self._model().DoesNotExist:
            raise FileNotFoundError(name)

    get_modified_time = get_created_time
    get_accessed_time = get_created_time

    def path(self, name):
        raise NotImplementedError('DatabaseStorage does not expose a filesystem path.')

    def generate_filename(self, filename):
        # Bypasses FileSystemStorage's OS-path validation; names here are
        # always POSIX-style keys, never real paths.
        dirname, basename = posixpath.split(str(filename).replace('\\', '/'))
        return posixpath.join(dirname, self.get_valid_name(basename))
