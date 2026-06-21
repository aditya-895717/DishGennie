"""
Template URL routes for accounts app — serves HTML pages.
"""
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import template_views

urlpatterns = [
    # ─── Auth pages ───
    path('accounts/login/', template_views.login_page, name='login'),
    path('accounts/signup/', template_views.signup_page, name='signup'),
    path('accounts/maid-register/', template_views.maid_register_page, name='maid-register'),
    path('accounts/logout/', template_views.logout_view, name='logout'),
    path('accounts/dashboard/', template_views.dashboard_redirect, name='dashboard-redirect'),
    path('accounts/verify-otp/', template_views.verify_otp_page, name='verify-otp'),

    # ─── Password Reset (Django built-in views with custom templates) ───
    path('accounts/forgot-password/', auth_views.PasswordResetView.as_view(
        template_name='accounts/forgot_password.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url=reverse_lazy('password-reset-done'),
    ), name='forgot-password'),
    path('accounts/forgot-password/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password-reset-done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('password-reset-complete'),
    ), name='password-reset-confirm'),
    path('accounts/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password-reset-complete'),

    # ─── User Panel ───
    path('', template_views.home_page, name='home'),
    path('dashboard/', template_views.user_dashboard, name='user-dashboard'),
    path('find-maid/', template_views.find_maid_page, name='find-maid'),
    path('maid/<int:pk>/', template_views.maid_profile_page, name='maid-profile'),
    path('book/', template_views.booking_flow_page, name='booking-flow'),
    path('confirmation/', template_views.confirmation_page, name='booking-confirmation'),
    path('my-bookings/', template_views.my_bookings_page, name='my-bookings'),
    path('live-tracking/<int:booking_id>/', template_views.live_tracking_page, name='live-tracking'),
    path('wallet/', template_views.wallet_page, name='wallet'),
    path('support/', template_views.support_page, name='support'),
    path('profile/', template_views.profile_page, name='user-profile'),

    # ─── Maid Panel ───
    path('maid-panel/', template_views.maid_dashboard, name='maid-dashboard'),
    path('maid-panel/requests/', template_views.maid_requests, name='maid-requests'),
    path('maid-panel/jobs/', template_views.maid_accepted_jobs, name='maid-jobs'),
    path('maid-panel/navigation/', template_views.maid_navigation, name='maid-navigation'),
    path('maid-panel/earnings/', template_views.maid_earnings, name='maid-earnings'),
    path('maid-panel/reviews/', template_views.maid_reviews, name='maid-reviews'),
    path('maid-panel/profile/', template_views.maid_profile_settings, name='maid-profile-settings'),

    # ─── Admin Panel ───
    path('admin-panel/', template_views.admin_dashboard, name='admin-dashboard'),
    path('admin-panel/users/', template_views.admin_users, name='admin-users'),
    path('admin-panel/maids/', template_views.admin_maids, name='admin-maids'),
    path('admin-panel/verification/', template_views.admin_verification, name='admin-verification'),
    path('admin-panel/bookings/', template_views.admin_bookings, name='admin-bookings'),
    path('admin-panel/payments/', template_views.admin_payments, name='admin-payments'),
    path('admin-panel/analytics/', template_views.admin_analytics, name='admin-analytics'),
    path('admin-panel/reports/', template_views.admin_reports, name='admin-reports'),
    path('admin-panel/disputes/', template_views.admin_disputes, name='admin-disputes'),
    path('admin-panel/settings/', template_views.admin_settings, name='admin-settings'),
]
