from django.urls import path
from . import views

urlpatterns = [
    path('initiate/', views.PaymentInitiateView.as_view(), name='api-payment-initiate'),
    path('verify/', views.PaymentVerifyView.as_view(), name='api-payment-verify'),
    path('wallet/', views.WalletView.as_view(), name='api-wallet'),
    path('wallet/add/', views.WalletAddView.as_view(), name='api-wallet-add'),
    path('subscriptions/', views.SubscriptionListView.as_view(), name='api-subscriptions'),
    path('subscriptions/subscribe/', views.SubscribeView.as_view(), name='api-subscribe'),
    path('maid/earnings/', views.MaidEarningsView.as_view(), name='api-maid-earnings'),
    path('admin/reports/', views.AdminPaymentReportsView.as_view(), name='api-admin-payments'),
    path('admin/list/', views.AdminPaymentListView.as_view(), name='api-admin-payment-list'),
]
