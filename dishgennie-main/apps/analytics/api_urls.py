from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.AdminDashboardView.as_view(), name='api-admin-dashboard'),
    path('revenue-chart/', views.RevenueChartView.as_view(), name='api-revenue-chart'),
    path('city-analytics/', views.CityAnalyticsView.as_view(), name='api-city-analytics'),
    path('service-analytics/', views.ServiceAnalyticsView.as_view(), name='api-service-analytics'),
]
