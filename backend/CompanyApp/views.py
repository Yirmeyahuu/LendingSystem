from django.shortcuts import render

# Create your views here.
def companyDashboard(request):
    return render(request, 'Company/companyDashboard.html')

def companyRegistration(request):
    return render(request, 'CompanyRegistration/registerCompany.html')