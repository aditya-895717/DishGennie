"""
Custom test runner that prevents any test, anywhere in the suite, from
hitting the live Brevo API.

Every email function in apps.accounts.email_utils (send_otp_email,
send_booking_confirmation, send_maid_notification, send_welcome_email,
notify_admin_new_registration) funnels through _get_api() and then calls
TransactionalEmailsApi.send_transac_email(). Patching that one SDK method
for the duration of the test run means no test can ever perform a real
network call to Brevo, regardless of which file or class it's in and
without requiring every test class to inherit from a shared base.
"""
from unittest.mock import MagicMock, patch

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class NoBrevoTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._brevo_patcher = patch(
            'sib_api_v3_sdk.TransactionalEmailsApi.send_transac_email',
            return_value=MagicMock(message_id='test-mocked-message-id'),
        )
        self._brevo_patcher.start()

        # Every send_* helper short-circuits to False when BREVO_API_KEY is
        # empty, which silently turns "email sent" branches into "email
        # failed" branches and fails unrelated tests. Pinning a dummy key
        # makes the suite independent of the developer's environment; the
        # patch above still guarantees no request leaves the machine.
        self._key_override = override_settings(
            BREVO_API_KEY='test-brevo-key-not-real',
            ADMIN_EMAIL='admin@example.test',
        )
        self._key_override.enable()

    def teardown_test_environment(self, **kwargs):
        self._key_override.disable()
        self._brevo_patcher.stop()
        super().teardown_test_environment(**kwargs)
