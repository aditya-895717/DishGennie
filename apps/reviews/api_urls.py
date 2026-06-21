from django.urls import path
from . import views

urlpatterns = [
    path('', views.ReviewCreateView.as_view(), name='api-review-create'),
    path('maid/<str:maid_id>/', views.MaidReviewsView.as_view(), name='api-maid-reviews'),
]
