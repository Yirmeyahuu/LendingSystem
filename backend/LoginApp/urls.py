from django.urls import path
from . import views

urlpatterns = [
    #Urls of Login Process

    #Url of user login
    path('login/', views.userLogin, name='user-login'),

    #Url of borrower logout
    path('logout/', views.userLogout, name='user-logout'),

    #Url of company logout
    path('logout/company/', views.companyLogout, name='company-logout'),

    # Password reset URLs
    path('forgot-password/', views.passwordResetRequest, name='password-reset-request'),
    path('reset-password/<uidb64>/<token>/', views.passwordResetConfirm, name='password-reset-confirm'),
]
