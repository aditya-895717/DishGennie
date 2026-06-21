from django.urls import path
from . import views

urlpatterns = [
    path('', views.BookingListCreateView.as_view(), name='api-bookings'),
    path('<int:pk>/', views.BookingDetailView.as_view(), name='api-booking-detail'),
    path('<int:pk>/accept/', views.AcceptBookingView.as_view(), name='api-booking-accept'),
    path('<int:pk>/reject/', views.RejectBookingView.as_view(), name='api-booking-reject'),
    path('<int:pk>/en-route/', views.EnRouteBookingView.as_view(), name='api-booking-en-route'),
    path('<int:pk>/start/', views.StartBookingView.as_view(), name='api-booking-start'),
    path('<int:pk>/complete/', views.CompleteBookingView.as_view(), name='api-booking-complete'),
    path('<int:pk>/cancel/', views.CancelBookingView.as_view(), name='api-booking-cancel'),
    path('maid/requests/', views.MaidPendingRequestsView.as_view(), name='api-maid-requests'),
    path('maid/active/', views.MaidActiveJobsView.as_view(), name='api-maid-active'),
]
