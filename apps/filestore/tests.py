"""
Tests for the database-backed media storage.

This backend exists because Vercel's filesystem is read-only, so it is the
only thing standing between a maid registration and a 500 in production —
the save/read/serve round trip and the access rules on KYC documents are
covered explicitly.
"""
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import CustomUser, MaidProfile

from .models import StoredFile
from .storage import DatabaseStorage

PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0'
    b'\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82'
)


class DatabaseStorageTests(TestCase):
    def setUp(self):
        self.storage = DatabaseStorage()

    def test_default_storage_is_database_backed(self):
        """A FileSystemStorage default would break on the first upload in
        production, so the wiring itself is worth asserting."""
        self.assertIsInstance(default_storage, DatabaseStorage)

    def test_save_and_read_round_trip(self):
        name = self.storage.save('maid_qr/example.png', ContentFile(PNG_BYTES))
        self.assertTrue(self.storage.exists(name))
        self.assertEqual(self.storage.size(name), len(PNG_BYTES))
        with self.storage.open(name) as handle:
            self.assertEqual(handle.read(), PNG_BYTES)

    def test_saved_bytes_land_in_the_database(self):
        self.storage.save('maid_qr/in_db.png', ContentFile(PNG_BYTES))
        record = StoredFile.objects.get(name='maid_qr/in_db.png')
        self.assertEqual(record.size, len(PNG_BYTES))
        self.assertEqual(record.content_type, 'image/png')

    def test_second_save_of_same_name_does_not_collide(self):
        first = self.storage.save('maid_qr/dup.png', ContentFile(PNG_BYTES))
        second = self.storage.save('maid_qr/dup.png', ContentFile(PNG_BYTES))
        self.assertNotEqual(first, second)
        self.assertTrue(self.storage.exists(first))
        self.assertTrue(self.storage.exists(second))

    def test_delete_removes_the_row(self):
        name = self.storage.save('maid_qr/gone.png', ContentFile(PNG_BYTES))
        self.storage.delete(name)
        self.assertFalse(self.storage.exists(name))
        self.assertFalse(StoredFile.objects.filter(name=name).exists())

    def test_url_points_at_the_media_route(self):
        self.assertEqual(self.storage.url('maid_qr/a.png'), '/media/maid_qr/a.png')

    def test_missing_file_raises_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.storage.open('maid_qr/never_saved.png')

    def test_path_traversal_is_refused(self):
        with self.assertRaises(SuspiciousFileOperation):
            self.storage.save('../../etc/passwd', ContentFile(b'nope'))

    @override_settings(FILESTORE_MAX_UPLOAD_BYTES=16)
    def test_oversized_upload_is_refused(self):
        with self.assertRaises(SuspiciousFileOperation):
            self.storage.save('maid_qr/big.png', ContentFile(b'x' * 64))
        self.assertFalse(StoredFile.objects.filter(name='maid_qr/big.png').exists())

    def test_model_field_save_uses_database_storage(self):
        user = CustomUser.objects.create_user(
            username='storage_maid', password='pass1234', role=CustomUser.Role.MAID,
        )
        profile = MaidProfile.objects.create(user=user)
        profile.qr_code.save('qr.png', ContentFile(PNG_BYTES), save=True)

        profile.refresh_from_db()
        self.assertTrue(StoredFile.objects.filter(name=profile.qr_code.name).exists())
        self.assertTrue(profile.qr_code.url.startswith('/media/'))


class ServeMediaViewTests(TestCase):
    def setUp(self):
        self.qr_name = default_storage.save('maid_qr/public.png', ContentFile(PNG_BYTES))

        self.owner = CustomUser.objects.create_user(
            username='doc_owner', password='pass1234', role=CustomUser.Role.MAID,
        )
        self.profile = MaidProfile.objects.create(user=self.owner)
        self.profile.aadhaar_document.save(
            'aadhaar.pdf', ContentFile(b'%PDF-1.4 sensitive'), save=True,
        )
        self.doc_name = self.profile.aadhaar_document.name

    def _url(self, name):
        return reverse('serve-media', args=[name])

    def test_public_file_is_served_with_its_content_type(self):
        response = self.client.get(self._url(self.qr_name))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(b''.join(response.streaming_content), PNG_BYTES)

    def test_unknown_file_is_404(self):
        response = self.client.get(self._url('maid_qr/missing.png'))
        self.assertEqual(response.status_code, 404)

    def test_kyc_document_is_hidden_from_anonymous_visitors(self):
        response = self.client.get(self._url(self.doc_name))
        self.assertEqual(response.status_code, 403)

    def test_kyc_document_is_hidden_from_another_maid(self):
        CustomUser.objects.create_user(
            username='nosy_maid', password='pass1234', role=CustomUser.Role.MAID,
        )
        self.client.login(username='nosy_maid', password='pass1234')
        response = self.client.get(self._url(self.doc_name))
        self.assertEqual(response.status_code, 403)

    def test_kyc_document_is_visible_to_its_owner(self):
        self.client.login(username='doc_owner', password='pass1234')
        response = self.client.get(self._url(self.doc_name))
        self.assertEqual(response.status_code, 200)

    def test_kyc_document_is_visible_to_admin(self):
        CustomUser.objects.create_user(
            username='kyc_admin', password='pass1234', role=CustomUser.Role.ADMIN,
        )
        self.client.login(username='kyc_admin', password='pass1234')
        response = self.client.get(self._url(self.doc_name))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 sensitive')
