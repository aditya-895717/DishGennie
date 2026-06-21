from django.urls import path
from . import views

urlpatterns = [
    path('cities/', views.CityListView.as_view(), name='api-cities'),
    path('categories/', views.ServiceCategoryListView.as_view(), name='api-categories'),
]
