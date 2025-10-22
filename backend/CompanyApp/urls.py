from django.urls import path
from . import views, admin_views

urlpatterns = [
    #Urls of Company Registration
    path('Registration/', views.companyRegistration, name='company-registration'),
    path('RegistrationSuccess/', views.companyRegistrationSuccess, name='company-registration-success'),

    #Urls of Company Content
    path('Dashboard/', views.companyDashboard, name='company-dashboard'),
    path('Loan-Applications/', views.loanApplication, name='company-loan-applications'),
    path('Borrower-Lists/', views.borrowerLists, name='company-borrower-lists'),
    path('Active-Loans/', views.activeLoans, name='company-active-loans'),
    path('Reports/', views.reports, name='company-reports'),
    path('Settings/', views.settings, name='company-settings'),
    path('company-active-borrowers/', views.activeBorrowers, name='company-active-borrowers'),
    path('company-potential-borrowers/', views.potentialBorrowers, name='company-potential-borrowers'),
    path('company-archived-borrowers/', views.archivedBorrowers, name='company-archived-borrowers'),
    path('company-add-borrowers/', views.addBorrowers, name='company-add-borrowers'),
    path('financial-reports/', views.financialReports, name='company-financial-reports'),
    path('portfolio-health/', views.portfolioHealth, name='company-portfolio-health'),
    path('operational-reports/', views.operationalReports, name='company-operational-reports'),


    # Admin approval URLs
    path('admin/approve/<int:company_id>/', admin_views.approve_company, name='admin:company_approve'),
    path('admin/reject/<int:company_id>/', admin_views.reject_company, name='admin:company_reject'),
]
