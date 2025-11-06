from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth import logout

class RoleBasedAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Define public URLs that authenticated users shouldn't access
        self.public_only_urls = [
            reverse('user-login'),
            reverse('borrower-registration'),
            reverse('company-registration'),
        ]
        # URLs that should be accessible to authenticated users without profiles
        self.profile_setup_urls = [
            '/profile/setup/',  # Add your profile setup URL
            '/accounts/logout/',  # Allow logout
        ]

    def __call__(self, request):
        # Allow profile setup and logout URLs
        if any(request.path.startswith(url) for url in self.profile_setup_urls):
            response = self.get_response(request)
            return response
        
        # Redirect authenticated users away from public-only pages
        if request.user.is_authenticated and self.is_public_only_page(request):
            return self.redirect_to_correct_dashboard(request)
        
        # Process the request before the view
        if request.user.is_authenticated:
            # Check if user is trying to access wrong portal
            if self.is_borrower_accessing_company(request) or self.is_company_accessing_borrower(request):
                messages.error(request, "You don't have permission to access this area.")
                return self.redirect_to_correct_dashboard(request)
        
        response = self.get_response(request)
        return response
    
    def is_public_only_page(self, request):
        """Check if the current page should only be accessible to non-authenticated users"""
        try:
            return any(request.path == url or request.path.startswith(url) for url in self.public_only_urls)
        except:
            # If reverse() fails, check by path patterns
            public_patterns = ['/login/', '/register/', '/landing/', '/Borrower-Registration/', '/Company-Registration/']
            return any(request.path.startswith(pattern) for pattern in public_patterns)

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
            # User is authenticated but has no profile - logout and redirect
            messages.warning(request, "Your account has no profile. Please contact support or register again.")
            logout(request)
            return redirect('landing-page')