"""
URL configuration for Dishgennie project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from home import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('service/', views.service, name='service'),
    path('contact/', views.contact, name='contact'),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.user_logout, name='logout'),
    path('subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', views.admin_manage_users, name='admin_manage_users'),
    path('admin/contact/delete/<int:contact_id>/', views.admin_delete_contact, name='admin_delete_contact'),
    path('admin/contact/reply/<int:contact_id>/', views.admin_reply_contact, name='admin_reply_contact'),
    path('admin/user/toggle/<int:user_id>/', views.admin_toggle_user_status, name='admin_toggle_user_status'),
     path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


