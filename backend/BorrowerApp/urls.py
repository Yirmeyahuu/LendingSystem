from django.urls import path
from . import views

urlpatterns = [
    #Urls of Borrower Content

    #Url of dashboard content
    path('Dashboard/', views.borrowerDashboard, name='borrower-dashboard'),
    #Url of Active loan content
    path('active-loan/', views.activeLoans, name='borrower-active-loan'),
    #Url of Loan history content
    path('loan-history/', views.loanHistory, name='borrower-loan-history'),
    #Url of Apply Loan content
    path('apply-loan/', views.applyLoan, name='borrower-apply-loan'),
    #Url of Payment content
    path('payments/', views.borrowerPayments, name='borrower-payments'),
    #Url of Borrower profile content
    path('profile/', views.borrowerProfile, name='borrower-profile'),
    #Url of Borrower Change password content
    path('change-password/', views.changePassword, name='borrower-change-password'),
    #Url of Security questions
    path('profile/security-questions/', views.update_security_questions, name='update_security_questions'),

    #Logout Url
    path('logout/', views.borrower_logout, name='borrower-logout'),
]
