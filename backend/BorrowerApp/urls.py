from django.urls import path
from . import views

urlpatterns = [
    #Urls of Borrower Registration
    path('Registration/', views.registerBorrower, name='borrower-registration'),
    path('RegistrationSuccess/', views.borrowerRegistrationSuccess, name='borrower-registration-success'),

    #Urls of Borrower Content
    path('Dashboard/', views.borrowerDashboard, name='borrower-dashboard'),
    path('active-loans/', views.activeLoans, name='active-loans'),
    path('active-loan/', views.activeLoans, name='borrower-active-loan'),
    path('loan-history/', views.loanHistory, name='borrower-loan-history'),
    path('apply-loan/', views.applyLoan, name='borrower-apply-loan'),
    path('payments/', views.borrowerPayments, name='borrower-payments'),
    path('profile/', views.borrowerProfile, name='borrower-profile'),
    path('change-password/', views.changePassword, name='borrower-change-password'),
    path('profile/security-questions/', views.update_security_questions, name='update_security_questions'),

    #Logout Url
    path('logout/', views.borrower_logout, name='borrower-logout'),
]
