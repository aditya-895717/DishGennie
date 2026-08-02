import os
import shutil
import tempfile
import time
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.filestore.models import StoredFile

from .email_utils import send_booking_confirmation, send_maid_notification
from .models import CustomUser, MaidProfile

_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='dishgennie_test_media_')
_CLEANUP_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='dishgennie_test_cleanup_media_')
_EMAIL_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='dishgennie_test_email_media_')
_RACE_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='dishgennie_test_race_media_')
_DOC_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='dishgennie_test_doc_media_')

# Minimal valid 1x1 PNG so ImageField validation accepts it as a real image.
PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0'
    b'\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82'
)


def _register_maid(client, extra=None, include_aadhaar=True):
    data = {
        'first_name': 'Test',
        'last_name': 'Maid',
        'username': 'testmaid1',
        'email': 'testmaid1@example.com',
        'phone': '9876543210',
        'password': 'testpass123',
        'password_confirm': 'testpass123',
        'aadhaar_number': '',
        'experience_years': '2',
        'hourly_rate': '250',
        'bio': 'Experienced maid',
    }
    if include_aadhaar:
        data['aadhaar_document'] = SimpleUploadedFile(
            'aadhaar.pdf', b'%PDF-1.4 fake aadhaar content', content_type='application/pdf',
        )
    if extra:
        data.update(extra)
    return client.post(reverse('maid-register'), data)


def _verify_otp(client):
    session = client.session
    pending = session['pending_registration']
    return client.post(reverse('verify-otp'), {'otp': pending['otp'], 'action': 'verify'})


@override_settings(MEDIA_ROOT=_TEST_MEDIA_ROOT)
class MaidRegistrationPaymentDetailsTests(TestCase):
    """These tests only assert on MaidProfile fields, not email behavior.
    (Brevo itself is mocked globally for the whole suite — see
    dishgennie/test_runner.py — so no per-class email mocking is needed here.)"""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)

    def test_registration_with_qr_and_upi_persists_to_profile(self):
        qr_file = SimpleUploadedFile('qr.png', PNG_BYTES, content_type='image/png')
        response = _register_maid(self.client, {'upi_id': 'testmaid@upi', 'qr_code': qr_file})
        self.assertEqual(response.status_code, 302)
        self.assertIn('pending_registration', self.client.session)

        _verify_otp(self.client)

        user = CustomUser.objects.get(username='testmaid1')
        profile = MaidProfile.objects.get(user=user)
        self.assertEqual(profile.upi_id, 'testmaid@upi')
        self.assertTrue(profile.qr_code.name)
        self.assertTrue(profile.qr_code.name.endswith('qr.png') or 'qr' in profile.qr_code.name)

    def test_registration_without_payment_details_still_succeeds(self):
        response = _register_maid(self.client)
        self.assertEqual(response.status_code, 302)

        _verify_otp(self.client)

        user = CustomUser.objects.get(username='testmaid1')
        profile = MaidProfile.objects.get(user=user)
        self.assertEqual(profile.upi_id, '')
        self.assertFalse(profile.qr_code)

    def test_registration_with_aadhaar_document_persists_to_profile(self):
        response = _register_maid(self.client)
        self.assertEqual(response.status_code, 302)
        self.assertIn('pending_registration', self.client.session)

        _verify_otp(self.client)

        user = CustomUser.objects.get(username='testmaid1')
        profile = MaidProfile.objects.get(user=user)
        self.assertTrue(profile.aadhaar_document.name)
        self.assertIn('aadhaar', profile.aadhaar_document.name.lower())

    def test_registration_without_aadhaar_document_is_rejected(self):
        response = _register_maid(self.client, include_aadhaar=False)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aadhaar document is required for verification.')
        self.assertNotIn('pending_registration', self.client.session)
        self.assertFalse(CustomUser.objects.filter(username='testmaid1').exists())


@override_settings(MEDIA_ROOT=_EMAIL_TEST_MEDIA_ROOT)
class RegistrationEmailTests(TestCase):
    """The live registration UI goes through template_views.verify_otp_page,
    not the RegisterView/MaidRegisterView DRF endpoints — both paths are
    covered here since both create real accounts."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_EMAIL_TEST_MEDIA_ROOT, ignore_errors=True)

    @patch('apps.accounts.template_views.notify_admin_new_registration')
    @patch('apps.accounts.template_views.send_welcome_email')
    def test_maid_template_flow_sends_welcome_and_admin_emails(self, mock_notify_admin, mock_welcome):
        _register_maid(self.client)
        _verify_otp(self.client)

        user = CustomUser.objects.get(username='testmaid1')
        mock_welcome.assert_called_once_with(user)
        mock_notify_admin.assert_called_once_with(user)

    @patch('apps.accounts.template_views.notify_admin_new_registration')
    @patch('apps.accounts.template_views.send_welcome_email')
    def test_customer_template_flow_sends_welcome_and_admin_emails(self, mock_notify_admin, mock_welcome):
        self.client.post(reverse('signup'), {
            'first_name': 'Test',
            'last_name': 'Customer',
            'username': 'testcustomer1',
            'email': 'testcustomer1@example.com',
            'phone': '9876543211',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
        })
        _verify_otp(self.client)

        user = CustomUser.objects.get(username='testcustomer1')
        mock_welcome.assert_called_once_with(user)
        mock_notify_admin.assert_called_once_with(user)

    @patch('apps.accounts.views.notify_admin_new_registration')
    @patch('apps.accounts.views.send_welcome_email')
    def test_api_register_view_sends_welcome_and_admin_emails(self, mock_notify_admin, mock_welcome):
        client = APIClient()
        response = client.post('/api/v1/accounts/register/', {
            'username': 'apicustomer1',
            'email': 'apicustomer1@example.com',
            'first_name': 'Api',
            'last_name': 'Customer',
            'phone': '9876543212',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
        })
        self.assertEqual(response.status_code, 201)
        user = CustomUser.objects.get(username='apicustomer1')
        mock_welcome.assert_called_once_with(user)
        mock_notify_admin.assert_called_once_with(user)

    @patch('apps.accounts.views.notify_admin_new_registration')
    @patch('apps.accounts.views.send_welcome_email')
    def test_api_maid_register_view_sends_welcome_and_admin_emails(self, mock_notify_admin, mock_welcome):
        client = APIClient()
        response = client.post('/api/v1/accounts/maid-register/', {
            'username': 'apimaid1',
            'email': 'apimaid1@example.com',
            'first_name': 'Api',
            'last_name': 'Maid',
            'phone': '9876543213',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
        })
        self.assertEqual(response.status_code, 201)
        user = CustomUser.objects.get(username='apimaid1')
        mock_welcome.assert_called_once_with(user)
        mock_notify_admin.assert_called_once_with(user)


class MaidVerificationTests(TestCase):
    """Covers both the new dedicated approve/reject endpoints and the
    existing action-based endpoint the live admin panel already calls —
    both paths share apps.accounts.views._approve_maid_profile /
    _reject_maid_profile, so both must now send the maid a notification."""

    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='admin1', password='pass1234', role=CustomUser.Role.ADMIN,
        )
        self.maid_user = CustomUser.objects.create_user(
            username='pending_maid', password='pass1234', role=CustomUser.Role.MAID,
        )
        self.profile = MaidProfile.objects.create(user=self.maid_user)

    @patch('apps.accounts.views.send_maid_approval_email')
    def test_dedicated_approve_endpoint(self, mock_approval_email):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        response = client.post(f'/api/v1/accounts/maids/{self.profile.pk}/approve/', {'remarks': 'Looks good'})

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.maid_user.refresh_from_db()
        self.assertEqual(self.profile.verification_status, MaidProfile.VerificationStatus.APPROVED)
        self.assertEqual(self.profile.verification_remarks, 'Looks good')
        self.assertTrue(self.maid_user.is_verified)
        mock_approval_email.assert_called_once_with(self.maid_user)

    @patch('apps.accounts.views.send_maid_rejection_email')
    def test_dedicated_reject_endpoint(self, mock_rejection_email):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        response = client.post(f'/api/v1/accounts/maids/{self.profile.pk}/reject/', {'reason': 'Incomplete documents'})

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.maid_user.refresh_from_db()
        self.assertEqual(self.profile.verification_status, MaidProfile.VerificationStatus.REJECTED)
        self.assertFalse(self.maid_user.is_active)
        mock_rejection_email.assert_called_once_with(self.maid_user, 'Incomplete documents')

    def test_approve_endpoint_rejects_non_admin(self):
        client = APIClient()
        client.force_authenticate(user=self.maid_user)
        response = client.post(f'/api/v1/accounts/maids/{self.profile.pk}/approve/', {})
        self.assertEqual(response.status_code, 403)

    @patch('apps.accounts.views.send_maid_approval_email')
    def test_existing_action_based_endpoint_now_sends_approval_email(self, mock_approval_email):
        """The live admin_panel/maid_verification.html page calls this exact
        endpoint with {action: 'approve'} — confirms it wasn't left behind."""
        client = APIClient()
        client.force_authenticate(user=self.admin)
        response = client.post(
            f'/api/v1/accounts/admin/verify/{self.profile.pk}/',
            {'action': 'approve', 'remarks': 'ok'},
        )
        self.assertEqual(response.status_code, 200)
        mock_approval_email.assert_called_once_with(self.maid_user)

    @patch('apps.accounts.views.send_maid_rejection_email')
    def test_existing_action_based_endpoint_now_sends_rejection_email(self, mock_rejection_email):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        response = client.post(
            f'/api/v1/accounts/admin/verify/{self.profile.pk}/',
            {'action': 'reject', 'remarks': 'not eligible'},
        )
        self.assertEqual(response.status_code, 200)
        mock_rejection_email.assert_called_once_with(self.maid_user, 'not eligible')


@override_settings(MEDIA_ROOT=_DOC_TEST_MEDIA_ROOT)
class AdminMaidDocumentVisibilityTests(TestCase):
    """Approve/reject is meaningless if the admin can't actually see the KYC
    document being verified — MaidProfileSerializer must expose a working
    aadhaar_document URL (it previously omitted the field entirely, so the
    admin verification page had no data to link to)."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_DOC_TEST_MEDIA_ROOT, ignore_errors=True)

    def test_pending_maid_list_includes_aadhaar_document_url(self):
        admin = CustomUser.objects.create_user(
            username='doc_admin', password='pass1234', role=CustomUser.Role.ADMIN,
        )
        maid_user = CustomUser.objects.create_user(
            username='doc_maid', password='pass1234', role=CustomUser.Role.MAID,
        )
        profile = MaidProfile.objects.create(user=maid_user)
        profile.aadhaar_document.save(
            'aadhaar_test.pdf', ContentFile(b'%PDF-1.4 fake aadhaar content'), save=True,
        )

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/v1/accounts/admin/maids/?status=pending')
        self.assertEqual(response.status_code, 200)

        results = response.data.get('results', response.data)
        matching = [r for r in results if r['id'] == profile.pk]
        self.assertEqual(len(matching), 1)
        aadhaar_url = matching[0]['aadhaar_document']
        self.assertTrue(aadhaar_url)
        self.assertIn('aadhaar_test', aadhaar_url)


class RegistrationDuplicateUsernameTests(TestCase):
    """Reproduces the reported bug: username uniqueness is a DB-level
    constraint regardless of is_active, so the pre-OTP check must not
    filter by is_active either — otherwise a deactivated/rejected user's
    username silently passes validation and later crashes create_user()."""

    def test_customer_signup_blocks_existing_active_username(self):
        CustomUser.objects.create_user(
            username='taken', email='existing@example.com',
            password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        response = self.client.post(reverse('signup'), {
            'first_name': 'New', 'last_name': 'User', 'username': 'taken',
            'email': 'newuser@example.com', 'phone': '9999999999',
            'password': 'testpass123', 'password_confirm': 'testpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already taken')
        self.assertNotIn('pending_registration', self.client.session)

    def test_customer_signup_blocks_username_taken_by_inactive_user(self):
        CustomUser.objects.create_user(
            username='rejected_maid', email='rejected@example.com', password='pass1234',
            role=CustomUser.Role.MAID, is_active=False,
        )
        response = self.client.post(reverse('signup'), {
            'first_name': 'New', 'last_name': 'User', 'username': 'rejected_maid',
            'email': 'newuser2@example.com', 'phone': '9999999998',
            'password': 'testpass123', 'password_confirm': 'testpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already taken')
        self.assertNotIn('pending_registration', self.client.session)

    @override_settings(MEDIA_ROOT=_RACE_TEST_MEDIA_ROOT)
    def test_maid_registration_blocks_username_taken_by_inactive_user(self):
        CustomUser.objects.create_user(
            username='rejected_maid2', email='rejected2@example.com', password='pass1234',
            role=CustomUser.Role.MAID, is_active=False,
        )
        response = _register_maid(self.client, {'username': 'rejected_maid2', 'email': 'newmaid@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already taken')
        self.assertNotIn('pending_registration', self.client.session)


@override_settings(MEDIA_ROOT=_RACE_TEST_MEDIA_ROOT)
class RegistrationRaceConditionTests(TestCase):
    """A username can pass the pre-OTP check and still collide at
    create_user() time if someone else takes it while the first user is
    sitting on the OTP screen. This must fail gracefully (redirect + clean
    message + session/temp-file cleanup), not a raw 500."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_RACE_TEST_MEDIA_ROOT, ignore_errors=True)

    def test_customer_verify_otp_handles_username_race(self):
        response = self.client.post(reverse('signup'), {
            'first_name': 'Race', 'last_name': 'Customer', 'username': 'race_user',
            'email': 'race_customer@example.com', 'phone': '9999999997',
            'password': 'testpass123', 'password_confirm': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)
        pending = self.client.session['pending_registration']

        # Someone else takes the same username before OTP verification completes.
        CustomUser.objects.create_user(
            username='race_user', email='someoneelse@example.com',
            password='pass1234', role=CustomUser.Role.CUSTOMER,
        )

        response = self.client.post(reverse('verify-otp'), {'otp': pending['otp'], 'action': 'verify'})
        self.assertRedirects(response, reverse('signup'))
        self.assertNotIn('pending_registration', self.client.session)
        self.assertEqual(CustomUser.objects.filter(username='race_user').count(), 1)

    def test_maid_verify_otp_handles_username_race(self):
        response = _register_maid(self.client, {'username': 'race_maid', 'email': 'race_maid@example.com'})
        self.assertEqual(response.status_code, 302)
        pending = self.client.session['pending_registration']
        aadhaar_path = pending.get('aadhaar_document_path')
        self.assertTrue(aadhaar_path)
        self.assertTrue(default_storage.exists(aadhaar_path))

        # Someone else takes the same username before OTP verification completes.
        CustomUser.objects.create_user(
            username='race_maid', email='someoneelsemaid@example.com',
            password='pass1234', role=CustomUser.Role.MAID,
        )

        response = self.client.post(reverse('verify-otp'), {'otp': pending['otp'], 'action': 'verify'})
        self.assertRedirects(response, reverse('maid-register'))
        self.assertNotIn('pending_registration', self.client.session)
        self.assertEqual(CustomUser.objects.filter(username='race_maid').count(), 1)
        # The failed attempt's MaidProfile must not have been created (atomic rollback).
        self.assertEqual(MaidProfile.objects.filter(user__username='race_maid').count(), 0)
        # And its temp Aadhaar upload must have been cleaned up, not left behind.
        self.assertFalse(default_storage.exists(aadhaar_path))


class ApiRegistrationRaceConditionTests(TestCase):
    """Same race as the template flow (Part 2 audit), but via the DRF
    endpoints. UniqueValidator on username already blocks the common case;
    this simulates the narrow window where two requests both pass
    validation before either writes, to confirm the fallback IntegrityError
    handling in RegisterView/MaidRegisterView returns a clean 400, not a raw
    500 from an unhandled exception."""

    @patch('apps.accounts.serializers.UserRegistrationSerializer.create')
    def test_register_view_handles_integrity_error(self, mock_create):
        mock_create.side_effect = IntegrityError('UNIQUE constraint failed: accounts_customuser.username')
        client = APIClient()
        response = client.post('/api/v1/accounts/register/', {
            'username': 'raceuser', 'email': 'race@example.com',
            'first_name': 'Race', 'last_name': 'User', 'phone': '9998887777',
            'password': 'testpass123', 'password_confirm': 'testpass123',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('taken', response.data.get('error', ''))

    @patch('apps.accounts.serializers.MaidRegistrationSerializer.create')
    def test_maid_register_view_handles_integrity_error(self, mock_create):
        mock_create.side_effect = IntegrityError('UNIQUE constraint failed: accounts_customuser.username')
        client = APIClient()
        response = client.post('/api/v1/accounts/maid-register/', {
            'username': 'racemaid', 'email': 'racemaid@example.com',
            'first_name': 'Race', 'last_name': 'Maid', 'phone': '9998887778',
            'password': 'testpass123', 'password_confirm': 'testpass123',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('taken', response.data.get('error', ''))


class EmailGuardTests(TestCase):
    """send_booking_confirmation / send_maid_notification must fail closed
    when BREVO_API_KEY is blank, matching the guard already used by
    send_otp_email / send_welcome_email / notify_admin_new_registration.
    Verified the same way as Block 3.1: the real transport layer is made to
    raise if it's ever reached, proving the guard short-circuits first."""

    def _fake_booking(self):
        return SimpleNamespace(pk=1, scheduled_date=None, service='Cleaning')

    @override_settings(BREVO_API_KEY='')
    def test_send_booking_confirmation_fails_closed_without_key(self):
        with patch(
            'sib_api_v3_sdk.rest.RESTClientObject.request',
            side_effect=AssertionError('REAL NETWORK CALL ATTEMPTED'),
        ):
            result = send_booking_confirmation('user@example.com', self._fake_booking(), 'Test User')
        self.assertFalse(result)

    @override_settings(BREVO_API_KEY='')
    def test_send_maid_notification_fails_closed_without_key(self):
        with patch(
            'sib_api_v3_sdk.rest.RESTClientObject.request',
            side_effect=AssertionError('REAL NETWORK CALL ATTEMPTED'),
        ):
            result = send_maid_notification('maid@example.com', self._fake_booking(), 'Test Maid')
        self.assertFalse(result)


@override_settings(MEDIA_ROOT=_CLEANUP_TEST_MEDIA_ROOT)
class CleanupAbandonedMaidUploadsTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_CLEANUP_TEST_MEDIA_ROOT, ignore_errors=True)

    def _make_temp_file(self, subdir, name, age_hours):
        path = default_storage.save(f'{subdir}/{name}', ContentFile(b'test content'))
        # Uploads live in Postgres now, so "age" is the stored row's
        # created_at rather than a filesystem mtime. auto_now_add ignores
        # assignment, hence the queryset update.
        StoredFile.objects.filter(name=path).update(
            created_at=timezone.now() - timedelta(hours=age_hours),
        )
        return path

    def test_old_temp_file_is_deleted(self):
        path = self._make_temp_file('tmp_maid_qr', 'old_qr.png', age_hours=48)

        out = StringIO()
        call_command('cleanup_abandoned_maid_uploads', stdout=out)

        self.assertFalse(default_storage.exists(path))
        self.assertIn('Deleted 1 stale temp upload', out.getvalue())

    def test_fresh_temp_file_is_kept(self):
        path = self._make_temp_file('tmp_maid_aadhaar', 'fresh_doc.pdf', age_hours=1)

        out = StringIO()
        call_command('cleanup_abandoned_maid_uploads', stdout=out)

        self.assertTrue(default_storage.exists(path))
        self.assertIn('Deleted 0 stale temp upload', out.getvalue())


class NearbyMaidSearchTests(TestCase):
    """Architecture.md §5.4 specifies a radius-based query on lat/lng. The
    maid list only ever filtered on city *name*, so "nearby" was a text
    search — a maid 400 km away in a same-named suburb ranked identically to
    one on the next street."""

    ORIGIN = {'lat': 26.9124, 'lng': 75.7873}  # Jaipur

    def _make_maid(self, username, lat=None, lng=None, account_lat=None, account_lng=None,
                   status=MaidProfile.VerificationStatus.APPROVED, available=True):
        user = CustomUser.objects.create_user(
            username=username, password='pass1234', role=CustomUser.Role.MAID,
            latitude=account_lat, longitude=account_lng,
        )
        return MaidProfile.objects.create(
            user=user, verification_status=status, is_available=available,
            current_lat=lat, current_lng=lng,
        )

    def _search(self, **params):
        query = {'lat': self.ORIGIN['lat'], 'lng': self.ORIGIN['lng']}
        query.update(params)
        response = self.client.get('/api/v1/accounts/maids/', query)
        self.assertEqual(response.status_code, 200)
        return response.json().get('results', response.json())

    def test_maid_inside_the_radius_is_returned_with_a_distance(self):
        self._make_maid('near_maid', lat=26.9200, lng=75.7900)  # ~0.9 km away
        results = self._search(radius_km=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'near_maid')
        self.assertLess(results[0]['distance_km'], 5)

    def test_maid_outside_the_radius_is_excluded(self):
        self._make_maid('far_maid', lat=28.6139, lng=77.2090)  # Delhi, ~240 km
        self.assertEqual(self._search(radius_km=10), [])

    def test_results_are_ordered_nearest_first(self):
        self._make_maid('mid_maid', lat=26.9500, lng=75.8200)
        self._make_maid('closest_maid', lat=26.9130, lng=75.7880)
        self._make_maid('outer_maid', lat=27.0100, lng=75.8600)

        results = self._search(radius_km=50)
        self.assertEqual(
            [row['name'] for row in results],
            ['closest_maid', 'mid_maid', 'outer_maid'],
        )
        distances = [row['distance_km'] for row in results]
        self.assertEqual(distances, sorted(distances))

    def test_account_coordinates_are_used_when_no_live_fix_exists(self):
        """A maid who has never shared a live location must still be findable
        from the coordinates saved on her profile page."""
        self._make_maid('base_only_maid', account_lat=26.9180, account_lng=75.7850)
        results = self._search(radius_km=10)
        self.assertEqual([row['name'] for row in results], ['base_only_maid'])

    def test_live_fix_wins_over_stale_account_coordinates(self):
        self._make_maid(
            'moved_maid', lat=28.6139, lng=77.2090,
            account_lat=26.9124, account_lng=75.7873,
        )
        self.assertEqual(self._search(radius_km=10), [])

    def test_unverified_and_unavailable_maids_never_appear(self):
        self._make_maid('pending_maid', lat=26.9130, lng=75.7880,
                        status=MaidProfile.VerificationStatus.PENDING)
        self._make_maid('busy_maid', lat=26.9130, lng=75.7880, available=False)
        self.assertEqual(self._search(radius_km=10), [])

    def test_maid_with_no_coordinates_at_all_is_skipped(self):
        self._make_maid('nowhere_maid')
        self.assertEqual(self._search(radius_km=100), [])

    def test_search_without_coordinates_keeps_the_plain_listing(self):
        """Omitting lat/lng must not silently return nothing — the city/rating
        filters are still the default browse experience."""
        self._make_maid('listed_maid', lat=28.6139, lng=77.2090)
        response = self.client.get('/api/v1/accounts/maids/')
        self.assertEqual(response.status_code, 200)
        results = response.json().get('results', response.json())
        self.assertEqual([row['name'] for row in results], ['listed_maid'])
        self.assertIsNone(results[0]['distance_km'])

    def test_garbage_coordinates_fall_back_to_the_plain_listing(self):
        self._make_maid('listed_maid2', lat=28.6139, lng=77.2090)
        response = self.client.get('/api/v1/accounts/maids/', {'lat': 'abc', 'lng': '999'})
        self.assertEqual(response.status_code, 200)
        results = response.json().get('results', response.json())
        self.assertEqual(len(results), 1)

    def test_radius_is_capped_so_a_huge_value_cannot_scan_the_planet(self):
        self._make_maid('sydney_maid', lat=-33.8688, lng=151.2093)
        self.assertEqual(self._search(radius_km=100000), [])
