from django.urls import path
from . import views, admin_views

urlpatterns = [
    #Urls of Company Content

    #Url of Company Dashboard
    path('Dashboard/', views.companyDashboard, name='company-dashboard'),

    #Url of Company Loan Application
    path('Loan-Applications/', views.loanApplication, name='company-loan-applications'),
    # Loan Application URLs
    path('Loan-Applications/<int:application_id>/view/', views.viewLoanApplication, name='view-loan-application-ajax'),
    path('Loan-Applications/<int:application_id>/approve/', views.approve_loan_application, name='approve-loan-application'),
    path('Loan-Applications/<int:application_id>/reject/', views.reject_loan_application, name='reject-loan-application'),
    path('Borrower-Lists/<int:borrower_id>/view/', views.viewBorrowerDetails, name='view-borrower-details'),

    # Replace the archived borrowers URLs with:
    path('Application-History/', views.applicationHistory, name='company-application-history'),

    #Url of Company Borrower List
    path('Borrower-Lists/', views.borrowerLists, name='company-borrower-lists'),

    #Url of Company Active Loans
    path('Active-Loans/', views.activeLoans, name='company-active-loans'),
    path('Active-Loans/<int:loan_id>/view-borrower/', views.viewBorrowerDetailsFromLoan, name='view-borrower-from-loan'),

    #Url of Company Settings
    path('Settings/', views.settings, name='company-settings'),

    #Url of Company Active Borrowers
    path('company-active-borrowers/', views.activeBorrowers, name='company-active-borrowers'),


    #Url of Company Add Borrowers
    path('company-add-borrowers/', views.addBorrowers, name='company-add-borrowers'),


    # Admin approval URLs
    path('admin/approve/<int:company_id>/', admin_views.approve_company, name='admin:company_approve'),
    path('admin/reject/<int:company_id>/', admin_views.reject_company, name='admin:company_reject'),
]