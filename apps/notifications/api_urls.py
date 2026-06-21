from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='api-notifications'),
    path('summary/', views.NotificationSummaryView.as_view(), name='api-notification-summary'),
    path('read/', views.MarkReadView.as_view(), name='api-notif-read-all'),
    path('read/<int:pk>/', views.MarkReadView.as_view(), name='api-notif-read'),
    path('broadcast/', views.BroadcastView.as_view(), name='api-broadcast'),
]
