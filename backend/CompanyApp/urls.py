from django.urls import path
from . import views, admin_views

urlpatterns = [
    path('Dashboard/', views.companyDashboard, name='company-dashboard'),
    path('Registration/', views.companyRegistration, name='company-registration'),
    path('RegistrationSuccess/', views.companyRegistrationSuccess, name='company-registration-success'),
    path('logout/', views.companyLogout, name='company-logout'),

    # Admin approval URLs
    path('admin/approve/<int:company_id>/', admin_views.approve_company, name='admin:company_approve'),
    path('admin/reject/<int:company_id>/', admin_views.reject_company, name='admin:company_reject'),
]
