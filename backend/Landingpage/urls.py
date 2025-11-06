from django.urls import path
from . import views

urlpatterns = [
    #Urls of landing Page App

    #Url of landing page
    path('', views.landingPage, name='landing-page'),

    #Url of Borrower Registration
    path('Borrower-Registration/', views.registerBorrower, name='borrower-registration'),

    #Url of Borrower Success Registration
    path('Borrower-Registration/Success/', views.borrowerRegistrationSuccess, name='borrower-registration-success'),

    #Url of Company Registration
    path('Company-Registration/', views.companyRegistration, name='company-registration'),

    #Url of Company Success Registration
    path('Company-Registration/Success/', views.companyRegistrationSuccess, name='company-registration-success'),
]
