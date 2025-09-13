from django.urls import path
from . import views

urlpatterns = [
    path('Dashboard/', views.companyDashboard, name='company-dashboard'),
]
