from django.urls import path
from . import views

urlpatterns = [
    path('', views.userLogin, name='user-login'),
]
