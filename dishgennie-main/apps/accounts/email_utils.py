import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_otp_email(to_email, otp_code, user_name=""):
    try:
        subject = "DishGennie — Your Verification Code"
        message = f"""Hi {user_name},

Your OTP verification code is: {otp_code}

This code expires in 10 minutes.
Do not share this with anyone.

— DishGennie Team"""
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info("OTP email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Email send failed to %s: %s", to_email, e)
        return False


def send_booking_confirmation(to_email, booking_details):
    try:
        subject = "DishGennie — Booking Confirmed"
        message = f"""Your booking has been confirmed.

Booking ID: {booking_details.get('id')}
Service: {booking_details.get('service')}
Date: {booking_details.get('date')}
Maid: {booking_details.get('maid_name')}

Thank you for choosing DishGennie!"""
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error("Booking email failed: %s", e)
        return False
