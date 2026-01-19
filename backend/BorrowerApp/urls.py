from django.urls import path
from . import views

urlpatterns = [
    # Public loan application flow (no authentication)
    path('select-company/', views.selectCompany, name='select-company'),
    path('application/<int:company_id>/', views.borrowerApplication, name='borrower-application'),
    path('application/success/', views.applicationSuccess, name='application-success'),
    path('check-existing-borrower/<int:company_id>/', views.check_existing_borrower, name='check-existing-borrower'),
]