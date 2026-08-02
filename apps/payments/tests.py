from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from apps.accounts.models import CustomUser
from apps.services.models import ServiceCategory
from apps.bookings.models import Booking
from .models import Payment, Subscription, UserSubscription


class ManualPaymentConfirmationTests(APITestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create_user(
            username='customer_a', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.maid_assigned = CustomUser.objects.create_user(
            username='maid_assigned', password='pass1234', role=CustomUser.Role.MAID,
        )
        self.maid_other = CustomUser.objects.create_user(
            username='maid_other', password='pass1234', role=CustomUser.Role.MAID,
        )
        self.service = ServiceCategory.objects.create(name='Cleaning', slug='cleaning')
        self.booking = Booking.objects.create(
            customer=self.customer,
            maid=self.maid_assigned,
            service=self.service,
            address='123 Test St',
            total_amount=500,
        )

    def test_assigned_maid_can_confirm_upi(self):
        self.client.force_authenticate(user=self.maid_assigned)
        url = reverse('api-payment-confirm-upi', args=[self.booking.pk])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(booking=self.booking)
        self.assertEqual(payment.method, Payment.Method.UPI)
        self.assertEqual(payment.status, Payment.Status.CONFIRMED)
        self.assertIsNotNone(payment.confirmed_by_maid_at)

    def test_assigned_maid_can_confirm_cash(self):
        self.client.force_authenticate(user=self.maid_assigned)
        url = reverse('api-payment-confirm-cash', args=[self.booking.pk])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(booking=self.booking)
        self.assertEqual(payment.method, Payment.Method.CASH)
        self.assertEqual(payment.status, Payment.Status.CONFIRMED)

    def test_unassigned_maid_cannot_confirm(self):
        self.client.force_authenticate(user=self.maid_other)
        url = reverse('api-payment-confirm-upi', args=[self.booking.pk])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Payment.objects.filter(booking=self.booking).exists())

    def test_customer_cannot_confirm(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('api-payment-confirm-cash', args=[self.booking.pk])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PaymentInitiateViewTests(APITestCase):
    """Payment.booking is a OneToOneField — calling initiate twice for the
    same booking used to raise an unhandled IntegrityError (500). Covers
    that this now fails gracefully via get_or_create, and that an invalid
    booking_id returns a clean 404 instead of a DoesNotExist crash."""

    def setUp(self):
        self.customer = CustomUser.objects.create_user(
            username='payer1', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.service = ServiceCategory.objects.create(name='Cleaning', slug='cleaning-payinit')
        self.booking = Booking.objects.create(
            customer=self.customer, service=self.service, address='Test St', total_amount=300,
        )

    def test_initiate_twice_does_not_crash(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('api-payment-initiate')
        first = self.client.post(url, {'booking_id': self.booking.pk, 'method': 'upi', 'amount': 300})
        self.assertEqual(first.status_code, 200)
        second = self.client.post(url, {'booking_id': self.booking.pk, 'method': 'upi', 'amount': 300})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['payment_id'], second.data['payment_id'])
        self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 1)

    def test_initiate_with_invalid_booking_returns_404(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('api-payment-initiate')
        response = self.client.post(url, {'booking_id': 999999, 'method': 'upi', 'amount': 300})
        self.assertEqual(response.status_code, 404)


class CustomerPaymentPageReachabilityTests(TestCase):
    """The payment page was only reachable by being on the live-tracking tab
    at the instant the maid marked the job complete; My Bookings offered no
    route to it. Covers that both the page and the link source render."""

    def setUp(self):
        self.customer = CustomUser.objects.create_user(
            username='reach_customer', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.service = ServiceCategory.objects.create(name='Cleaning', slug='cleaning-reach')
        self.booking = Booking.objects.create(
            customer=self.customer, service=self.service, address='7 Test St',
            status=Booking.Status.COMPLETED, total_amount=350,
        )

    def test_payment_page_renders_for_the_owning_customer(self):
        self.client.login(username='reach_customer', password='pass1234')
        response = self.client.get(reverse('payment-page', args=[self.booking.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/payment.html')

    def test_my_bookings_offers_a_route_to_the_payment_page(self):
        self.client.login(username='reach_customer', password='pass1234')
        response = self.client.get(reverse('my-bookings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/payments/${booking.id}/')

    def test_payment_page_requires_login(self):
        response = self.client.get(reverse('payment-page', args=[self.booking.pk]))
        self.assertEqual(response.status_code, 302)


class SubscriptionPageTests(TestCase):
    """subscriptions_page existed as an orphan: no URL, no template and no
    link, despite a fully working subscriptions API behind it."""

    def setUp(self):
        self.customer = CustomUser.objects.create_user(
            username='sub_customer', password='pass1234', role=CustomUser.Role.CUSTOMER,
        )
        self.plan = Subscription.objects.create(
            name='Gold', slug='gold', price=999, duration_days=30,
            visits_per_month=8, discount_percent=15,
        )

    def test_subscriptions_page_is_routed_and_renders(self):
        self.client.login(username='sub_customer', password='pass1234')
        response = self.client.get(reverse('subscriptions'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/subscriptions.html')

    def test_subscriptions_page_is_linked_from_the_sidebar(self):
        self.client.login(username='sub_customer', password='pass1234')
        response = self.client.get(reverse('user-dashboard'))
        self.assertContains(response, reverse('subscriptions'))

    def test_subscribing_activates_a_plan(self):
        self.client.force_login(self.customer)
        api = APIClient()
        api.force_authenticate(user=self.customer)
        response = api.post(reverse('api-subscribe'), {'plan_id': self.plan.pk})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            UserSubscription.objects.filter(user=self.customer, plan=self.plan, is_active=True).exists()
        )
