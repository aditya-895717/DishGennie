from django.urls import path
from . import views

urlpatterns = [
    path('tickets/', views.TicketListCreateView.as_view(), name='api-tickets'),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name='api-ticket-detail'),
]
