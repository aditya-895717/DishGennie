"""
API URL routes for accounts app.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='api-register'),
    path('maid-register/', views.MaidRegisterView.as_view(), name='api-maid-register'),
    path('login/', views.LoginView.as_view(), name='api-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='api-token-refresh'),
    path('profile/', views.ProfileView.as_view(), name='api-profile'),
    path('maid-profile/', views.MaidProfileView.as_view(), name='api-maid-profile'),
    path('maids/', views.MaidListView.as_view(), name='api-maid-list'),
    path('maids/<int:pk>/', views.MaidDetailView.as_view(), name='api-maid-detail'),
    path('admin/users/', views.AdminUserListView.as_view(), name='api-admin-users'),
    path('admin/maids/', views.AdminMaidProfileListView.as_view(), name='api-admin-maids'),
    path('admin/verify/<int:pk>/', views.AdminMaidVerificationView.as_view(), name='api-admin-verify'),
]
