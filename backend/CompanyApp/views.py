from django.shortcuts import render

# Create your views here.
def companyDashboard(request):
    return render(request, 'company/companyDashboard.html')