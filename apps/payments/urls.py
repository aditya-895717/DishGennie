from django.urls import path
from . import template_views

urlpatterns = [
    path('<int:booking_id>/', template_views.payment_page, name='payment-page'),
]
