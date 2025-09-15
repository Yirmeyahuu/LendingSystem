from django.shortcuts import render

# Create your views here.
def registerBorrower(request):
    return render(request, 'BorrowerRegistration/registerBorrower.html')