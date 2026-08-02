from django.urls import path
from . import views

urlpatterns = [
    path('update/', views.UpdateLocationView.as_view(), name='api-location-update'),
    # Architecture.md §6 names this route `status/<booking_id>/`; the bare
    # `<booking_id>/` form is what shipped first and stays as an alias.
    path('status/<int:booking_id>/', views.GetLocationView.as_view(), name='api-location-status'),
    path('<int:booking_id>/', views.GetLocationView.as_view(), name='api-location-get'),
]
