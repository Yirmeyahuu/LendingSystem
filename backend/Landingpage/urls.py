from django.urls import path
from . import views

urlpatterns = [
    path('', views.landingPage, name='landing-page'),
    #Urls of Borrower Registration
    path('Borrower-Registration/', views.registerBorrower, name='borrower-registration'),
    path('Borrower-Registration/Success/', views.borrowerRegistrationSuccess, name='borrower-registration-success'),

    #Urls of Company Registration
    path('Company-Registration/', views.companyRegistration, name='company-registration'),
    path('Company-Registration/Success/', views.companyRegistrationSuccess, name='company-registration-success'),
]
