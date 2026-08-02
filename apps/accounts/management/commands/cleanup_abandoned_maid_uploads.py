"""
Deletes stale temp uploads left behind by abandoned maid registrations.

QR code / Aadhaar document files are saved to tmp_maid_qr/ or
tmp_maid_aadhaar/ as soon as they're uploaded (see maid_register_page),
then moved onto the MaidProfile and deleted from the temp path once OTP
verification completes (see verify_otp_page). Any temp file still present
past the grace period therefore belongs to a registration that was never
completed — no separate MaidProfile lookup is needed to tell.
"""
from datetime import timedelta

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

TEMP_DIRS = ['tmp_maid_qr', 'tmp_maid_aadhaar']


class Command(BaseCommand):
    help = 'Deletes abandoned maid registration temp uploads (QR code / Aadhaar document) older than --hours.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours', type=float, default=24,
            help='Delete temp files older than this many hours (default: 24).',
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=options['hours'])
        deleted = 0

        for temp_dir in TEMP_DIRS:
            try:
                _, filenames = default_storage.listdir(temp_dir)
            except (FileNotFoundError, OSError):
                continue

            for filename in filenames:
                path = f'{temp_dir}/{filename}'
                try:
                    modified_at = default_storage.get_modified_time(path)
                except (FileNotFoundError, OSError):
                    continue
                if timezone.is_naive(modified_at):
                    modified_at = timezone.make_aware(modified_at)
                if modified_at < cutoff:
                    default_storage.delete(path)
                    deleted += 1

        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} stale temp upload(s).'))
