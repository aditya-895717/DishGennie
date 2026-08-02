from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from apps.accounts.models import CustomUser, MaidProfile
from apps.services.models import ServiceCategory
from apps.bookings.models import Booking
from .models import LocationUpdate


class TrackingIDORTests(APITestCase):
    """Booking A must stay invisible to unrelated user B and to an unassigned maid."""

    def setUp(self):
        self.customer_a = CustomUser.objects.create_user(
            username='customer_a', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.customer_b = CustomUser.objects.create_user(
            username='customer_b', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.maid_assigned = CustomUser.objects.create_user(
            username='maid_assigned', password='pass1234', role=CustomUser.Role.MAID,
        )
        self.maid_other = CustomUser.objects.create_user(
            username='maid_other', password='pass1234', role=CustomUser.Role.MAID,
        )
        self.service = ServiceCategory.objects.create(name='Cleaning', slug='cleaning')
        self.booking = Booking.objects.create(
            customer=self.customer_a,
            maid=self.maid_assigned,
            service=self.service,
            address='123 Test St',
        )

    def test_unrelated_user_cannot_fetch_location(self):
        LocationUpdate.objects.create(
            booking=self.booking, maid=self.maid_assigned, latitude=12.9, longitude=77.6,
        )
        self.client.force_authenticate(user=self.customer_b)
        url = reverse('api-location-get', args=[self.booking.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owning_customer_can_fetch_location(self):
        LocationUpdate.objects.create(
            booking=self.booking, maid=self.maid_assigned, latitude=12.9, longitude=77.6,
        )
        self.client.force_authenticate(user=self.customer_a)
        url = reverse('api-location-get', args=[self.booking.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unassigned_maid_cannot_post_location(self):
        self.client.force_authenticate(user=self.maid_other)
        url = reverse('api-location-update')
        response = self.client.post(url, {
            'booking_id': self.booking.pk, 'latitude': 12.9, 'longitude': 77.6,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(LocationUpdate.objects.filter(booking=self.booking, maid=self.maid_other).exists())

    def test_assigned_maid_can_post_location(self):
        self.client.force_authenticate(user=self.maid_assigned)
        url = reverse('api-location-update')
        response = self.client.post(url, {
            'booking_id': self.booking.pk, 'latitude': 12.9, 'longitude': 77.6,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(LocationUpdate.objects.filter(booking=self.booking, maid=self.maid_assigned).exists())


class TrackingStatusContractTests(APITestCase):
    """Architecture.md §6 defines GET /tracking/status/<booking_id>/ as
    returning {lat, lng, updated_at, maid_status}. The shipped endpoint used
    different key names, omitted the status, and 404'd before the first fix
    arrived — which is the normal state at the start of every booking."""

    def setUp(self):
        self.customer = CustomUser.objects.create_user(
            username='status_customer', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.maid = CustomUser.objects.create_user(
            username='status_maid', password='pass1234', role=CustomUser.Role.MAID,
        )
        self.profile = MaidProfile.objects.create(user=self.maid)
        self.service = ServiceCategory.objects.create(name='Cleaning', slug='cleaning-status')
        self.booking = Booking.objects.create(
            customer=self.customer, maid=self.maid, service=self.service,
            address='9 Test St', status=Booking.Status.MAID_EN_ROUTE,
        )

    def test_status_route_exists_under_the_documented_path(self):
        self.assertEqual(
            reverse('api-location-status', args=[self.booking.pk]),
            f'/api/v1/tracking/status/{self.booking.pk}/',
        )

    def test_no_location_yet_returns_200_with_nulls_not_404(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(reverse('api-location-status', args=[self.booking.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['lat'])
        self.assertIsNone(response.data['lng'])
        self.assertIsNone(response.data['updated_at'])
        self.assertEqual(response.data['maid_status'], Booking.Status.MAID_EN_ROUTE)

    def test_documented_keys_are_present_once_a_fix_arrives(self):
        LocationUpdate.objects.create(
            booking=self.booking, maid=self.maid, latitude=26.9124, longitude=75.7873,
        )
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(reverse('api-location-status', args=[self.booking.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['lat']), 26.9124)
        self.assertEqual(float(response.data['lng']), 75.7873)
        self.assertIsNotNone(response.data['updated_at'])
        self.assertEqual(response.data['maid_status'], Booking.Status.MAID_EN_ROUTE)

    def test_latest_fix_wins(self):
        LocationUpdate.objects.create(
            booking=self.booking, maid=self.maid, latitude=26.9000, longitude=75.7000,
        )
        LocationUpdate.objects.create(
            booking=self.booking, maid=self.maid, latitude=26.9500, longitude=75.8000,
        )
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(reverse('api-location-status', args=[self.booking.pk]))
        self.assertEqual(float(response.data['lat']), 26.9500)

    def test_status_route_enforces_the_same_ownership_rule(self):
        stranger = CustomUser.objects.create_user(
            username='status_stranger', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.client.force_authenticate(user=stranger)
        response = self.client.get(reverse('api-location-status', args=[self.booking.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_posting_a_fix_denormalises_onto_the_maid_profile(self):
        """Architecture.md §6: the update endpoint must refresh
        current_lat/current_lng/last_location_update, which is what the
        nearby search reads."""
        self.client.force_authenticate(user=self.maid)
        response = self.client.post(reverse('api-location-update'), {
            'booking_id': self.booking.pk, 'latitude': 26.9124, 'longitude': 75.7873,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        self.assertEqual(float(self.profile.current_lat), 26.9124)
        self.assertEqual(float(self.profile.current_lng), 75.7873)
        self.assertIsNotNone(self.profile.last_location_update)

    def test_rejected_post_leaves_the_profile_untouched(self):
        other_maid = CustomUser.objects.create_user(
            username='status_other_maid', password='pass1234', role=CustomUser.Role.MAID,
        )
        other_profile = MaidProfile.objects.create(user=other_maid)
        self.client.force_authenticate(user=other_maid)
        self.client.post(reverse('api-location-update'), {
            'booking_id': self.booking.pk, 'latitude': 26.9124, 'longitude': 75.7873,
        })
        other_profile.refresh_from_db()
        self.assertIsNone(other_profile.current_lat)
        self.assertIsNone(other_profile.last_location_update)
