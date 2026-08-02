import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_api():
    config = sib_api_v3_sdk.Configuration()
    config.api_key['api-key'] = settings.BREVO_API_KEY
    return sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(config)
    )


def _parse_sender():
    # Parses "DishGennie <noreply@dishgennie.com>"
    # into {"name": "DishGennie", "email": "noreply@dishgennie.com"}
    raw = settings.DEFAULT_FROM_EMAIL
    if '<' in raw and '>' in raw:
        name = raw.split('<')[0].strip()
        email = raw.split('<')[1].replace('>', '').strip()
    else:
        name = "DishGennie"
        email = raw.strip()
    return {"name": name, "email": email}


def send_otp_email(to_email, otp_code, user_name="User"):
    if not settings.BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set — email cannot be sent")
        return False
    try:
        api = _get_api()
        msg = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email, "name": user_name}],
            sender=_parse_sender(),
            subject="DishGennie — Your Verification Code",
            html_content=(
                f'<div style="font-family:Arial,sans-serif;'
                f'max-width:480px;margin:auto;padding:24px">'
                f'<h2 style="color:#FF6B35;margin-bottom:4px">DishGennie</h2>'
                f'<p style="color:#666">Premium Maid Booking Platform</p>'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'<p>Hi <strong>{user_name}</strong>,</p>'
                f'<p>Your OTP verification code is:</p>'
                f'<div style="font-size:36px;font-weight:bold;letter-spacing:10px;'
                f'color:#2C3E50;background:#f8f9fa;padding:16px;border-radius:8px;'
                f'text-align:center;margin:16px 0">{otp_code}</div>'
                f'<p style="color:#e74c3c">This code expires in <strong>10 minutes</strong>.</p>'
                f'<p style="color:#999;font-size:13px">Do not share this with anyone.</p>'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'<p style="color:#999;font-size:12px">— DishGennie Team</p>'
                f'</div>'
            ),
            text_content=(
                f"Hi {user_name}, your OTP is: {otp_code}. "
                f"Expires in 10 minutes. Do not share."
            ),
        )
        api.send_transac_email(msg)
        logger.info("OTP sent to %s", to_email)
        return True
    except ApiException as e:
        logger.error("Brevo OTP ApiException: %s", e)
        return False
    except Exception as e:
        logger.error("OTP email unexpected error: %s", e)
        return False


def send_booking_confirmation(to_email, booking, user_name="User"):
    if not settings.BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set — email cannot be sent")
        return False
    try:
        date_display = booking.scheduled_date or "Instant"
        api = _get_api()
        msg = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email, "name": user_name}],
            sender=_parse_sender(),
            subject=f"DishGennie — Booking #{booking.pk} Confirmed",
            html_content=(
                f'<div style="font-family:Arial,sans-serif;'
                f'max-width:480px;margin:auto;padding:24px">'
                f'<h2 style="color:#FF6B35">Booking Confirmed!</h2>'
                f'<p>Hi <strong>{user_name}</strong>, your booking is confirmed.</p>'
                f'<table style="width:100%;border-collapse:collapse;margin:16px 0">'
                f'<tr style="background:#f8f9fa">'
                f'<td style="padding:10px;border:1px solid #eee"><strong>Booking ID</strong></td>'
                f'<td style="padding:10px;border:1px solid #eee">#{booking.pk}</td></tr>'
                f'<tr>'
                f'<td style="padding:10px;border:1px solid #eee"><strong>Service</strong></td>'
                f'<td style="padding:10px;border:1px solid #eee">{booking.service}</td></tr>'
                f'<tr style="background:#f8f9fa">'
                f'<td style="padding:10px;border:1px solid #eee"><strong>Date</strong></td>'
                f'<td style="padding:10px;border:1px solid #eee">{date_display}</td></tr>'
                f'<tr>'
                f'<td style="padding:10px;border:1px solid #eee"><strong>Status</strong></td>'
                f'<td style="padding:10px;border:1px solid #eee;'
                f'color:#27AE60;font-weight:bold">Confirmed</td></tr>'
                f'</table>'
                f'<p style="color:#27AE60;font-weight:bold">Thank you for choosing DishGennie!</p>'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'<p style="color:#999;font-size:12px">— DishGennie Team</p>'
                f'</div>'
            ),
        )
        api.send_transac_email(msg)
        logger.info("Booking confirmation sent to %s", to_email)
        return True
    except ApiException as e:
        logger.error("Brevo booking ApiException: %s", e)
        return False
    except Exception as e:
        logger.error("Booking email unexpected error: %s", e)
        return False


def send_maid_notification(to_email, booking, maid_name=""):
    if not settings.BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set — email cannot be sent")
        return False
    try:
        date_display = booking.scheduled_date or "Instant"
        api = _get_api()
        msg = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email, "name": maid_name}],
            sender=_parse_sender(),
            subject=f"DishGennie — New Booking Request #{booking.pk}",
            html_content=(
                f'<div style="font-family:Arial,sans-serif;'
                f'max-width:480px;margin:auto;padding:24px">'
                f'<h2 style="color:#FF6B35">New Booking Request!</h2>'
                f'<p>Hi <strong>{maid_name}</strong>, you have a new booking request.</p>'
                f'<p><strong>Booking ID:</strong> #{booking.pk}</p>'
                f'<p><strong>Service:</strong> {booking.service}</p>'
                f'<p><strong>Date:</strong> {date_display}</p>'
                f'<p>Please login to accept or reject this request.</p>'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'<p style="color:#999;font-size:12px">— DishGennie Team</p>'
                f'</div>'
            ),
        )
        api.send_transac_email(msg)
        logger.info("Maid notification sent to %s", to_email)
        return True
    except ApiException as e:
        logger.error("Brevo maid notification ApiException: %s", e)
        return False
    except Exception as e:
        logger.error("Maid notification unexpected error: %s", e)
        return False


def send_welcome_email(user):
    """Send a welcome email to a newly registered customer or maid."""
    if not settings.BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set — welcome email cannot be sent")
        return False

    name = user.get_full_name() or user.username
    is_maid = getattr(user, 'is_maid_user', False)

    if is_maid:
        subject = "Welcome to DishGennie — Partner Registration Received"
        body = (
            f'<p>Hi <strong>{name}</strong>, thanks for registering as a DishGennie partner!</p>'
            f'<p>Your profile is now <strong>pending admin verification</strong>. '
            f'You will be notified as soon as it is approved and you start appearing '
            f'in customer searches.</p>'
        )
    else:
        subject = "Welcome to DishGennie!"
        body = (
            f'<p>Hi <strong>{name}</strong>, welcome to DishGennie!</p>'
            f'<p>You can now find verified maids near you, track them live during a booking, '
            f'and pay via UPI or cash.</p>'
        )

    try:
        api = _get_api()
        msg = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": user.email, "name": name}],
            sender=_parse_sender(),
            subject=subject,
            html_content=(
                f'<div style="font-family:Arial,sans-serif;'
                f'max-width:480px;margin:auto;padding:24px">'
                f'<h2 style="color:#FF6B35;margin-bottom:4px">DishGennie</h2>'
                f'<p style="color:#666">Premium Maid Booking Platform</p>'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'{body}'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'<p style="color:#999;font-size:12px">— DishGennie Team</p>'
                f'</div>'
            ),
        )
        api.send_transac_email(msg)
        logger.info("Welcome email sent to %s", user.email)
        return True
    except ApiException as e:
        logger.error("Brevo welcome email ApiException: %s", e)
        return False
    except Exception as e:
        logger.error("Welcome email unexpected error: %s", e)
        return False


def notify_admin_new_registration(user):
    """Notify settings.ADMIN_EMAIL whenever a new customer or maid registers."""
    admin_email = getattr(settings, 'ADMIN_EMAIL', '')
    if not admin_email:
        logger.error("ADMIN_EMAIL not set — registration notification cannot be sent")
        return False
    if not settings.BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set — admin registration notification cannot be sent")
        return False

    name = user.get_full_name() or user.username
    role_label = "Maid/Partner" if getattr(user, 'is_maid_user', False) else "Customer"

    try:
        api = _get_api()
        msg = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": admin_email, "name": "DishGennie Admin"}],
            sender=_parse_sender(),
            subject=f"DishGennie — New {role_label} Registration: {name}",
            html_content=(
                f'<div style="font-family:Arial,sans-serif;'
                f'max-width:480px;margin:auto;padding:24px">'
                f'<h2 style="color:#FF6B35">New {role_label} Registration</h2>'
                f'<p><strong>Name:</strong> {name}</p>'
                f'<p><strong>Username:</strong> {user.username}</p>'
                f'<p><strong>Email:</strong> {user.email}</p>'
                f'<p><strong>Phone:</strong> {user.phone or "—"}</p>'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'<p style="color:#999;font-size:12px">— DishGennie System</p>'
                f'</div>'
            ),
        )
        api.send_transac_email(msg)
        logger.info("Admin notified of new %s registration: %s", role_label, user.username)
        return True
    except ApiException as e:
        logger.error("Brevo admin notification ApiException: %s", e)
        return False
    except Exception as e:
        logger.error("Admin notification unexpected error: %s", e)
        return False


def send_maid_approval_email(user):
    """Notify a maid that their verification was approved."""
    if not settings.BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set — approval email cannot be sent")
        return False

    name = user.get_full_name() or user.username
    try:
        api = _get_api()
        msg = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": user.email, "name": name}],
            sender=_parse_sender(),
            subject="DishGennie — You're Verified!",
            html_content=(
                f'<div style="font-family:Arial,sans-serif;'
                f'max-width:480px;margin:auto;padding:24px">'
                f'<h2 style="color:#FF6B35;margin-bottom:4px">DishGennie</h2>'
                f'<p style="color:#666">Premium Maid Booking Platform</p>'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'<p>Hi <strong>{name}</strong>, great news!</p>'
                f'<p>Your partner profile has been <strong style="color:#27AE60">approved</strong>. '
                f'You now appear in customer searches and can start accepting bookings.</p>'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'<p style="color:#999;font-size:12px">— DishGennie Team</p>'
                f'</div>'
            ),
        )
        api.send_transac_email(msg)
        logger.info("Approval email sent to %s", user.email)
        return True
    except ApiException as e:
        logger.error("Brevo approval email ApiException: %s", e)
        return False
    except Exception as e:
        logger.error("Approval email unexpected error: %s", e)
        return False


def send_maid_rejection_email(user, reason=""):
    """Notify a maid that their verification was rejected."""
    if not settings.BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set — rejection email cannot be sent")
        return False

    name = user.get_full_name() or user.username
    reason_html = f'<p><strong>Reason:</strong> {reason}</p>' if reason else ''
    try:
        api = _get_api()
        msg = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": user.email, "name": name}],
            sender=_parse_sender(),
            subject="DishGennie — Partner Application Update",
            html_content=(
                f'<div style="font-family:Arial,sans-serif;'
                f'max-width:480px;margin:auto;padding:24px">'
                f'<h2 style="color:#FF6B35;margin-bottom:4px">DishGennie</h2>'
                f'<p style="color:#666">Premium Maid Booking Platform</p>'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'<p>Hi <strong>{name}</strong>,</p>'
                f'<p>We were unable to verify your partner application at this time.</p>'
                f'{reason_html}'
                f'<p>If you believe this is a mistake or would like to reapply, please contact support.</p>'
                f'<hr style="border:none;border-top:1px solid #eee">'
                f'<p style="color:#999;font-size:12px">— DishGennie Team</p>'
                f'</div>'
            ),
        )
        api.send_transac_email(msg)
        logger.info("Rejection email sent to %s", user.email)
        return True
    except ApiException as e:
        logger.error("Brevo rejection email ApiException: %s", e)
        return False
    except Exception as e:
        logger.error("Rejection email unexpected error: %s", e)
        return False
