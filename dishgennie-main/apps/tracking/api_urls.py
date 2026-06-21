from django.urls import path
from . import views

urlpatterns = [
    path('update/', views.UpdateLocationView.as_view(), name='api-location-update'),
    path('<int:booking_id>/', views.GetLocationView.as_view(), name='api-location-get'),
]
