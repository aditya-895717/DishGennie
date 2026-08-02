"""
Template views for the payments app.
"""
from django.shortcuts import render
from apps.accounts.decorators import customer_required
from apps.accounts.template_views import _generate_jwt_context


@customer_required
def payment_page(request, booking_id):
    context = {'booking_id': booking_id}
    context.update(_generate_jwt_context(request.user))
    return render(request, 'user/payment.html', context)
