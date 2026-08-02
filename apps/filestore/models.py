"""
Database-backed media storage.

Vercel's serverless filesystem is read-only (except an ephemeral /tmp that
does not survive between invocations), so uploaded media — maid QR codes,
Aadhaar documents, avatars — cannot live on disk. Rather than introduce a
third-party blob provider, the bytes are stored in Neon Postgres alongside
everything else.

Volumes here are small by nature (a QR PNG and an ID document per maid), so
a bytea column is an appropriate fit. MAX_UPLOAD_BYTES keeps it that way.
"""
from django.db import models


class StoredFile(models.Model):
    """One uploaded file, addressed by the same relative path Django would
    have written to MEDIA_ROOT (e.g. 'maid_qr/abc.png')."""

    name = models.CharField(max_length=500, unique=True, db_index=True)
    content = models.BinaryField()
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stored File'
        verbose_name_plural = 'Stored Files'

    def __str__(self):
        return f"{self.name} ({self.size} bytes)"
