"""
Template views — render HTML pages for all 3 dashboards.
Handles server-side authentication (login/signup/logout) with Django sessions.
"""
import logging
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, MaidProfile
from .decorators import customer_required, maid_required, admin_required

logger = logging.getLogger(__name__)


# ──────────────────── HELPERS ────────────────────

def _redirect_by_role(user):
    """Redirect authenticated user to their role-based dashboard."""
    if user.is_admin_user:
        return redirect('admin-dashboard')
    elif user.is_maid_user:
        return redirect('maid-dashboard')
    return redirect('user-dashboard')


def _generate_jwt_context(user):
    """Generate JWT tokens to embed in the template for API calls."""
    refresh = RefreshToken.for_user(user)
    return {
        'jwt_access': str(refresh.access_token),
        'jwt_refresh': str(refresh),
    }


# ──────────────────── AUTH PAGES ────────────────────

@never_cache
def login_page(request):
    """Login page — GET shows form, POST authenticates."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember_me')

        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
            return render(request, 'accounts/login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, 'Your account has been disabled. Contact support.')
                return render(request, 'accounts/login.html')

            login(request, user)

            # Handle "Remember Me"
            if not remember:
                request.session.set_expiry(0)  # Session expires on browser close
            else:
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days

            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return _redirect_by_role(user)
        else:
            # Check if this is a rejected/deactivated maid trying to log in
            try:
                inactive_user = CustomUser.objects.get(username=username, is_active=False)
                if inactive_user.is_maid_user and hasattr(inactive_user, 'maid_profile'):
                    if inactive_user.maid_profile.verification_status == 'rejected':
                        messages.error(request, 'Your maid verification was rejected. Please re-register with updated details or contact support.')
                    else:
                        messages.error(request, 'Your account has been deactivated. Contact support.')
                else:
                    messages.error(request, 'Your account has been deactivated. Contact support.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'accounts/login.html')


@never_cache
def signup_page(request):
    """Customer signup — GET shows form, POST validates and sends OTP."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        referral_code_input = request.POST.get('referral_code', '').strip()

        # Validation
        errors = []
        if not username:
            errors.append('Username is required.')
        if not email:
            errors.append('Email is required for OTP verification.')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != password_confirm:
            errors.append('Passwords do not match.')

        try:
            if CustomUser.objects.filter(username=username, is_active=True).exists():
                errors.append('This username is already taken.')
            if email and CustomUser.objects.filter(email=email, is_active=True).exists():
                errors.append('This email is already registered.')
        except Exception as db_err:
            logger.error('Database error during signup validation: %s', db_err)
            messages.error(request, 'Service temporarily unavailable. Please try again later.')
            return render(request, 'accounts/signup.html', {'form_data': request.POST})

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'accounts/signup.html', {
                'form_data': request.POST
            })

        # Store registration data in session and send OTP
        try:
            otp = str(random.randint(100000, 999999))
            request.session['pending_registration'] = {
                'type': 'customer',
                'first_name': first_name,
                'last_name': last_name,
                'username': username,
                'email': email,
                'phone': phone,
                'password': password,
                'referral_code': referral_code_input,
                'otp': otp,
            }
            email_sent = _send_otp_email(email, otp, first_name or username)
            if email_sent:
                messages.info(request, f'A verification code has been sent to {email}')
            else:
                messages.warning(
                    request,
                    f'We could not send the verification email to {email}. '
                    f'Please check the address and try again.'
                )
                return render(request, 'accounts/signup.html', {'form_data': request.POST})
            return redirect('verify-otp')
        except Exception as exc:
            logger.error('Error during signup OTP flow: %s', exc, exc_info=True)
            messages.error(request, 'Something went wrong. Please try again.')
            return render(request, 'accounts/signup.html', {'form_data': request.POST})

    return render(request, 'accounts/signup.html')


@never_cache
def maid_register_page(request):
    """Maid partner registration — GET shows form, POST validates and sends OTP."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        aadhaar_number = request.POST.get('aadhaar_number', '').strip()
        experience_years = request.POST.get('experience_years', 0)
        hourly_rate = request.POST.get('hourly_rate', 200)
        bio = request.POST.get('bio', '').strip()

        # Validation
        errors = []
        if not username:
            errors.append('Username is required.')
        if not email:
            errors.append('Email is required for OTP verification.')
        if not phone:
            errors.append('Phone number is required.')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != password_confirm:
            errors.append('Passwords do not match.')

        try:
            if CustomUser.objects.filter(username=username, is_active=True).exists():
                errors.append('This username is already taken.')
            if email and CustomUser.objects.filter(email=email, is_active=True).exists():
                errors.append('This email is already registered.')
        except Exception as db_err:
            logger.error('Database error during maid registration validation: %s', db_err)
            messages.error(request, 'Service temporarily unavailable. Please try again later.')
            return render(request, 'accounts/maid_register.html', {'form_data': request.POST})

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'accounts/maid_register.html', {
                'form_data': request.POST
            })

        # Store registration data in session and send OTP
        try:
            otp = str(random.randint(100000, 999999))
            request.session['pending_registration'] = {
                'type': 'maid',
                'first_name': first_name,
                'last_name': last_name,
                'username': username,
                'email': email,
                'phone': phone,
                'password': password,
                'aadhaar_number': aadhaar_number,
                'experience_years': str(experience_years),
                'hourly_rate': str(hourly_rate),
                'bio': bio,
                'otp': otp,
            }
            email_sent = _send_otp_email(email, otp, first_name or username)
            if email_sent:
                messages.info(request, f'A verification code has been sent to {email}')
            else:
                messages.warning(
                    request,
                    f'We could not send the verification email to {email}. '
                    f'Please check the address and try again.'
                )
                return render(request, 'accounts/maid_register.html', {'form_data': request.POST})
            return redirect('verify-otp')
        except Exception as exc:
            logger.error('Error during maid registration OTP flow: %s', exc, exc_info=True)
            messages.error(request, 'Something went wrong. Please try again.')
            return render(request, 'accounts/maid_register.html', {'form_data': request.POST})

    return render(request, 'accounts/maid_register.html')


# ──────────────────── OTP VERIFICATION ────────────────────

def _send_otp_email(email, otp, name):
    """Send OTP verification email. Returns True on success, False on failure."""
    subject = f'DishGennie — Your Verification Code is {otp}'
    message = (
        f'Hi {name},\n\n'
        f'Your email verification code is: {otp}\n\n'
        f'This code is valid for 10 minutes. Do not share it with anyone.\n\n'
        f'— DishGennie Team'
    )
    html_message = (
        f'<div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;'
        f'border:1px solid #e5e7eb;border-radius:12px">'
        f'<h2 style="color:#0d6356;margin-bottom:4px">DishGennie</h2>'
        f'<p>Hi <strong>{name}</strong>,</p>'
        f'<p>Your email verification code is:</p>'
        f'<div style="text-align:center;margin:24px 0">'
        f'<span style="font-size:32px;font-weight:700;letter-spacing:8px;'
        f'background:#f0fdf4;padding:16px 32px;border-radius:8px;color:#0d6356">{otp}</span></div>'
        f'<p style="color:#6b7280;font-size:14px">This code is valid for 10 minutes. '
        f'Do not share it with anyone.</p>'
        f'<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">'
        f'<p style="color:#9ca3af;font-size:12px;text-align:center">'
        f'If you did not request this code, please ignore this email.</p></div>'
    )
    try:
        sent = send_mail(
            subject, message, settings.DEFAULT_FROM_EMAIL, [email],
            html_message=html_message, fail_silently=False,
        )
        if sent:
            logger.info('OTP email sent successfully to %s', email)
        else:
            logger.warning('send_mail returned 0 for %s', email)
        return bool(sent)
    except Exception as exc:
        logger.error('Failed to send OTP email to %s: %s', email, exc, exc_info=True)
        return False


@never_cache
def verify_otp_page(request):
    """OTP verification page — verifies email OTP and creates the user account."""
    pending = request.session.get('pending_registration')
    if not pending:
        messages.error(request, 'No pending registration found. Please sign up again.')
        return redirect('signup')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        action = request.POST.get('action', 'verify')

        # Resend OTP
        if action == 'resend':
            new_otp = str(random.randint(100000, 999999))
            pending['otp'] = new_otp
            request.session['pending_registration'] = pending
            email_sent = _send_otp_email(
                pending['email'], new_otp,
                pending.get('first_name') or pending['username'],
            )
            if email_sent:
                messages.success(request, f'A new code has been sent to {pending["email"]}')
            else:
                messages.warning(
                    request,
                    'Could not resend the verification email. Please try again in a moment.'
                )
            return render(request, 'accounts/verify_otp.html', {
                'email': pending['email'],
                'reg_type': pending['type'],
            })

        # Verify OTP
        if entered_otp != pending.get('otp'):
            messages.error(request, 'Invalid verification code. Please try again.')
            return render(request, 'accounts/verify_otp.html', {
                'email': pending['email'],
                'reg_type': pending['type'],
            })

        # OTP is valid — create the account
        try:
            if pending['type'] == 'customer':
                referred_by = None
                if pending.get('referral_code'):
                    try:
                        referred_by = CustomUser.objects.get(referral_code=pending['referral_code'])
                    except CustomUser.DoesNotExist:
                        pass

                user = CustomUser.objects.create_user(
                    username=pending['username'],
                    email=pending['email'],
                    first_name=pending['first_name'],
                    last_name=pending['last_name'],
                    phone=pending.get('phone', ''),
                    password=pending['password'],
                    role=CustomUser.Role.CUSTOMER,
                    referred_by=referred_by,
                    is_verified=True,
                )
                del request.session['pending_registration']
                login(request, user)
                messages.success(request, f'Welcome to DishGennie, {pending["first_name"] or pending["username"]}! 🎉')
                return redirect('user-dashboard')

            elif pending['type'] == 'maid':
                user = CustomUser.objects.create_user(
                    username=pending['username'],
                    email=pending['email'],
                    first_name=pending['first_name'],
                    last_name=pending['last_name'],
                    phone=pending.get('phone', ''),
                    password=pending['password'],
                    role=CustomUser.Role.MAID,
                    is_verified=True,
                )
                try:
                    exp = int(pending.get('experience_years', 0))
                except (ValueError, TypeError):
                    exp = 0
                try:
                    rate = float(pending.get('hourly_rate', 200))
                except (ValueError, TypeError):
                    rate = 200.00

                MaidProfile.objects.create(
                    user=user,
                    aadhaar_number=pending.get('aadhaar_number', ''),
                    experience_years=exp,
                    hourly_rate=rate,
                    bio=pending.get('bio', ''),
                )
                del request.session['pending_registration']
                login(request, user)
                messages.success(request, 'Registration successful! Your profile is pending admin verification.')
                return redirect('maid-dashboard')

        except Exception as exc:
            logger.error('Account creation failed: %s', exc, exc_info=True)
            messages.error(
                request,
                'We could not create your account right now. '
                'Please try again later or contact support.'
            )
            return render(request, 'accounts/verify_otp.html', {
                'email': pending['email'],
                'reg_type': pending['type'],
            })

    return render(request, 'accounts/verify_otp.html', {
        'email': pending['email'],
        'reg_type': pending['type'],
    })


@require_POST
def logout_view(request):
    """Logout — POST only. Clears Django session."""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def dashboard_redirect(request):
    """Redirect to the correct dashboard based on role."""
    return _redirect_by_role(request.user)


# ──────────────────── FORGOT / RESET PASSWORD ────────────────────
# These use Django's built-in auth views (configured in urls.py).
# Custom templates are in templates/accounts/


# ──────────────────── USER PANEL ────────────────────

def home_page(request):
    """Public landing page / user home."""
    context = {}
    if request.user.is_authenticated:
        context.update(_generate_jwt_context(request.user))
    return render(request, 'user/home.html', context)


@customer_required
def user_dashboard(request):
    """User dashboard with recent bookings and stats."""
    context = _generate_jwt_context(request.user)
    return render(request, 'user/dashboard.html', context)


@customer_required
def find_maid_page(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'user/find_maid.html', context)


@customer_required
def maid_profile_page(request, pk):
    context = {'maid_id': pk}
    context.update(_generate_jwt_context(request.user))
    return render(request, 'user/maid_profile.html', context)


@customer_required
def booking_flow_page(request):
    context = _generate_jwt_context(request.user)
    from apps.accounts.models import MaidProfile
    from apps.services.models import ServiceCategory

    selected_maid_profile = None
    maid_profile_id = request.GET.get('maid_profile')
    if maid_profile_id:
        selected_maid_profile = MaidProfile.objects.filter(
            pk=maid_profile_id,
            verification_status__in=[
                MaidProfile.VerificationStatus.APPROVED,
                'verified',
            ],
            is_available=True,
        ).select_related('user').first()

    context.update({
        'services': ServiceCategory.objects.filter(is_active=True),
        'selected_maid_profile': selected_maid_profile,
    })
    return render(request, 'user/booking_flow.html', context)


@customer_required
def my_bookings_page(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'user/my_bookings.html', context)


@customer_required
def live_tracking_page(request, booking_id):
    context = {'booking_id': booking_id}
    context.update(_generate_jwt_context(request.user))
    return render(request, 'user/live_tracking.html', context)


@customer_required
def confirmation_page(request):
    context = {
        'booking_id': request.GET.get('booking_id', ''),
    }
    context.update(_generate_jwt_context(request.user))
    return render(request, 'user/confirmation.html', context)


@customer_required
def wallet_page(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'user/wallet.html', context)


@customer_required
def subscriptions_page(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'user/subscriptions.html', context)


@login_required
def support_page(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'user/support.html', context)


@login_required
def profile_page(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'user/profile.html', context)


# ──────────────────── MAID PANEL ────────────────────

@maid_required
def maid_dashboard(request):
    context = _generate_jwt_context(request.user)
    profile = getattr(request.user, 'maid_profile', None)
    if profile:
        context['verification_status'] = profile.verification_status
        context['verification_remarks'] = profile.verification_remarks
        if profile.verification_status == 'rejected':
            return render(request, 'maid/rejected.html', context)
    return render(request, 'maid/dashboard.html', context)


@maid_required
def maid_requests(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'maid/new_requests.html', context)


@maid_required
def maid_accepted_jobs(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'maid/accepted_jobs.html', context)


@maid_required
def maid_navigation(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'maid/navigation.html', context)


@maid_required
def maid_earnings(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'maid/earnings.html', context)


@maid_required
def maid_reviews(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'maid/reviews.html', context)


@maid_required
def maid_profile_settings(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'maid/profile.html', context)


# ──────────────────── ADMIN PANEL ────────────────────

@admin_required
def admin_dashboard(request):
    context = _generate_jwt_context(request.user)
    # Pass city list for template rendering
    from apps.services.models import City
    context['cities'] = City.objects.filter(is_active=True)[:5]
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def admin_users(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'admin_panel/users.html', context)


@admin_required
def admin_maids(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'admin_panel/maids.html', context)


@admin_required
def admin_verification(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'admin_panel/maid_verification.html', context)


@admin_required
def admin_bookings(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'admin_panel/bookings.html', context)


@admin_required
def admin_payments(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'admin_panel/payments.html', context)


@admin_required
def admin_analytics(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'admin_panel/analytics.html', context)


@admin_required
def admin_reports(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'admin_panel/reports.html', context)


@admin_required
def admin_disputes(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'admin_panel/disputes.html', context)


@admin_required
def admin_settings(request):
    context = _generate_jwt_context(request.user)
    return render(request, 'admin_panel/settings.html', context)
