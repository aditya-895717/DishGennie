"""
Booking lifecycle tests covering the fields Architecture.md §4/§6 specify
and the payment state the customer-facing pages read.
"""
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import CustomUser
from apps.payments.models import Payment
from apps.services.models import ServiceCategory

from .models import Booking


class OtpVerificationTimestampTests(APITestCase):
    """Architecture.md §6: verifying the OTP must record otp_verified_at, not
    only flip the status. The field was missing entirely, so the moment of
    arrival was unrecoverable after the fact."""

    def setUp(self):
        self.customer = CustomUser.objects.create_user(
            username='otp_customer', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.maid = CustomUser.objects.create_user(
            username='otp_maid', password='pass1234', role=CustomUser.Role.MAID,
        )
        self.service = ServiceCategory.objects.create(name='Cleaning', slug='cleaning-otp')
        self.booking = Booking.objects.create(
            customer=self.customer, maid=self.maid, service=self.service,
            address='1 Test Road', status=Booking.Status.ACCEPTED, total_amount=400,
        )

    def test_correct_otp_records_verification_time(self):
        self.client.force_authenticate(user=self.maid)
        response = self.client.post(
            reverse('api-booking-start', args=[self.booking.pk]),
            {'otp': self.booking.otp},
        )
        self.assertEqual(response.status_code, 200)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.IN_PROGRESS)
        self.assertIsNotNone(self.booking.otp_verified_at)
        self.assertEqual(self.booking.otp_verified_at, self.booking.started_at)

    def test_wrong_otp_leaves_verification_time_unset(self):
        self.client.force_authenticate(user=self.maid)
        response = self.client.post(
            reverse('api-booking-start', args=[self.booking.pk]),
            {'otp': '000000'},
        )
        self.assertEqual(response.status_code, 400)

        self.booking.refresh_from_db()
        self.assertIsNone(self.booking.otp_verified_at)
        self.assertEqual(self.booking.status, Booking.Status.ACCEPTED)


class BookingPaymentStateTests(APITestCase):
    """my_bookings.html and payment.html decide whether to show "Pay Now" and
    the confirmation banner purely from these two serializer fields."""

    def setUp(self):
        self.customer = CustomUser.objects.create_user(
            username='pay_state_customer', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.maid = CustomUser.objects.create_user(
            username='pay_state_maid', password='pass1234', role=CustomUser.Role.MAID,
        )
        self.service = ServiceCategory.objects.create(name='Cleaning', slug='cleaning-paystate')
        self.booking = Booking.objects.create(
            customer=self.customer, maid=self.maid, service=self.service,
            address='2 Test Road', status=Booking.Status.COMPLETED, total_amount=600,
        )

    def _fetch(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(reverse('api-booking-detail', args=[self.booking.pk]))
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_booking_without_payment_reports_null_status(self):
        data = self._fetch()
        self.assertIsNone(data['payment_status'])
        self.assertIsNone(data['payment_method'])

    def test_confirmed_payment_is_reflected_on_the_booking(self):
        Payment.objects.create(
            booking=self.booking, user=self.customer, amount=600,
            method=Payment.Method.UPI, status=Payment.Status.CONFIRMED,
        )
        data = self._fetch()
        self.assertEqual(data['payment_status'], Payment.Status.CONFIRMED)
        self.assertEqual(data['payment_method'], Payment.Method.UPI)

    def test_maid_confirmation_flows_through_to_the_customer_view(self):
        """End-to-end of the manual confirmation loop: the maid presses the
        button on her page, the customer's polling picks it up."""
        self.client.force_authenticate(user=self.maid)
        confirm = self.client.post(reverse('api-payment-confirm-cash', args=[self.booking.pk]), {})
        self.assertEqual(confirm.status_code, 200)

        data = self._fetch()
        self.assertEqual(data['payment_status'], Payment.Status.CONFIRMED)
        self.assertEqual(data['payment_method'], Payment.Method.CASH)


class BookingLocationTests(APITestCase):
    """The booking form had no way to send coordinates, so every booking was
    created with NULL lat/lng and both maps fell back to hard-coded Mumbai."""

    def setUp(self):
        self.customer = CustomUser.objects.create_user(
            username='geo_customer', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.service = ServiceCategory.objects.create(name='Cleaning', slug='cleaning-geo')

    def test_booking_accepts_and_stores_coordinates(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(reverse('api-bookings'), {
            'service': self.service.pk,
            'booking_type': 'instant',
            'address': '3 Test Road',
            'duration_hours': 2,
            'total_amount': 500,
            'latitude': '26.912400',
            'longitude': '75.787300',
        })
        self.assertEqual(response.status_code, 201)

        booking = Booking.objects.get(pk=response.data['id'])
        self.assertEqual(float(booking.latitude), 26.9124)
        self.assertEqual(float(booking.longitude), 75.7873)
