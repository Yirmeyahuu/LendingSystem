from django.urls import path
from . import views, admin_views

urlpatterns = [
    #Urls of Company Content

    #Url of Company Dashboard
    path('Dashboard/', views.companyDashboard, name='company-dashboard'),

    #Url of Company Loan Application
    path('Loan-Applications/', views.loanApplication, name='company-loan-applications'),

    #Url of Company Borrower List
    path('Borrower-Lists/', views.borrowerLists, name='company-borrower-lists'),

    #Url of Company Active Loans
    path('Active-Loans/', views.activeLoans, name='company-active-loans'),

    #Url of Company Reports
    path('Reports/', views.reports, name='company-reports'),

    #Url of Company Settings
    path('Settings/', views.settings, name='company-settings'),

    #Url of Company Active Borrowers
    path('company-active-borrowers/', views.activeBorrowers, name='company-active-borrowers'),

    #Url of Company Potential Borrowers
    path('company-potential-borrowers/', views.potentialBorrowers, 
    name='company-potential-borrowers'),

    #Url of Company Archived Borrowers
    path('company-archived-borrowers/', views.archivedBorrowers, name='company-archived-borrowers'),

    #Url of Company Add Borrowers
    path('company-add-borrowers/', views.addBorrowers, name='company-add-borrowers'),

    #Url of Company Financial Reports
    path('financial-reports/', views.financialReports, name='company-financial-reports'),

    #Url of Company Portfolio Health
    path('portfolio-health/', views.portfolioHealth, name='company-portfolio-health'),

    #Url of Company Operational Reports
    path('operational-reports/', views.operationalReports, name='company-operational-reports'),


    # Admin approval URLs
    path('admin/approve/<int:company_id>/', admin_views.approve_company, name='admin:company_approve'),
    path('admin/reject/<int:company_id>/', admin_views.reject_company, name='admin:company_reject'),
]
