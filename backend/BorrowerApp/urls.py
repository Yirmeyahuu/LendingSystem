from django.urls import path
from . import views

urlpatterns = [
    path('Registration/', views.registerBorrower, name='borrower-registration'),
    path('Dashboard/', views.borrowerDashboard, name='borrower-dashboard'),

    path('RegistrationSuccess/', views.borrowerRegistrationSuccess, name='borrower-registration-success'),

    path('logout/', views.borrower_logout, name='borrower-logout'),
]
