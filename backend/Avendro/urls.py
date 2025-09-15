from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Landingpage.urls')),
    path('Company/', include('CompanyApp.urls')),
    path('Borrower/', include('BorrowerApp.urls')),
    path('Login/', include('LoginApp.urls')),


    path('__reload__/', include('django_browser_reload.urls')),
]
