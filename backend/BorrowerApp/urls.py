from django.urls import path
from . import views

urlpatterns = [
    #Urls of Borrower Registration
    path('Registration/', views.registerBorrower, name='borrower-registration'),
    path('RegistrationSuccess/', views.borrowerRegistrationSuccess, name='borrower-registration-success'),

    #Urls of Borrower Content
    path('Dashboard/', views.borrowerDashboard, name='borrower-dashboard'),

    #Logout Url
    path('logout/', views.borrower_logout, name='borrower-logout'),
]
