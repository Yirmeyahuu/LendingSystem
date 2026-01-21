from django.contrib import admin
from django.urls import path, include

# Import to apply custom admin settings
from . import admin as custom_admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Landingpage.urls')), #url of landing page
    path('Company/', include('CompanyApp.urls')), #url of Company User
    path('Borrower/', include('BorrowerApp.urls')),#url of borrower user
    path('Auth/', include('LoginApp.urls')), #url of authentication

    path('__reload__/', include('django_browser_reload.urls')), #django reload url
]