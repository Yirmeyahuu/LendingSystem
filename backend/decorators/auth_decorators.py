from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden

def borrower_required(view_func):
    """Decorator that requires user to be a borrower"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if hasattr(request.user, 'borrower_profile'):
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Access denied. Borrower account required.")
            if hasattr(request.user, 'company_profile'):
                return redirect('company-dashboard')
            return redirect('landing-page')
    return wrapper

def company_required(view_func):
    """Decorator that requires user to be a company"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if hasattr(request.user, 'company_profile'):
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Access denied. Company account required.")
            if hasattr(request.user, 'borrower_profile'):
                return redirect('borrower-dashboard')
            return redirect('landing-page')
    return wrapper

def user_type_required(user_type):
    """Generic decorator for user type requirements"""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if user_type == 'borrower' and hasattr(request.user, 'borrower_profile'):
                return view_func(request, *args, **kwargs)
            elif user_type == 'company' and hasattr(request.user, 'company_profile'):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, f"Access denied. {user_type.title()} account required.")
                return redirect('landing-page')
        return wrapper
    return decorator