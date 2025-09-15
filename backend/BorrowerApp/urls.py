from django.urls import path
from . import views

urlpatterns = [
    path('Registration/', views.registerBorrower, name='borrower-registration'),
]
