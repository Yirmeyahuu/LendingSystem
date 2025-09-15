from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden
from django.contrib import messages

class RoleBasedAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request before the view
        if request.user.is_authenticated:
            # Check if user is trying to access wrong portal
            if self.is_borrower_accessing_company(request) or self.is_company_accessing_borrower(request):
                messages.error(request, "You don't have permission to access this area.")
                return self.redirect_to_correct_dashboard(request)
        
        response = self.get_response(request)
        return response

    def is_borrower_accessing_company(self, request):
        """Check if a borrower is trying to access company URLs"""
        return (hasattr(request.user, 'borrower_profile') and 
                request.path.startswith('/company/'))

    def is_company_accessing_borrower(self, request):
        """Check if a company user is trying to access borrower URLs"""
        return (hasattr(request.user, 'company_profile') and 
                request.path.startswith('/borrower/'))

    def redirect_to_correct_dashboard(self, request):
        """Redirect user to their appropriate dashboard"""
        if hasattr(request.user, 'borrower_profile'):
            return redirect('borrower-dashboard')
        elif hasattr(request.user, 'company_profile'):
            return redirect('company-dashboard')
        else:
            return redirect('landing-page')