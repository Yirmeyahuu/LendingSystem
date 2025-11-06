from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from CompanyApp.models import Company
from decorators.auth_decorators import anonymous_required

#User login (Borrower or Company) Login function
@anonymous_required
def userLogin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_type = request.POST.get('user_type')  # 'borrower' or 'lender'
        remember_me = request.POST.get('remember-me')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user is active
            if not user.is_active:
                messages.error(request, 'Your account is not active. Please contact support.')
                return render(request, 'LoginApp/userLogin.html')
            
            # Validate user type selection matches user's actual type
            if user_type == 'lender':
                # Check if user is actually a company/lender
                try:
                    company = Company.objects.get(user=user)
                    if not company.is_approved:
                        messages.error(request, 'Your company account is pending approval.')
                        return render(request, 'LoginApp/userLogin.html')
                    
                    # Login successful for company
                    login(request, user)
                    
                    # Handle remember me
                    if not remember_me:
                        request.session.set_expiry(0)  # Session expires when browser closes
                    
                    messages.success(request, f'Welcome back, {company.company_name}!')
                    return redirect('company-dashboard')  # Redirect to company dashboard
                    
                except Company.DoesNotExist:
                    messages.error(request, 'No company account found. Please register as a lending company first.')
                    return render(request, 'LoginApp/userLogin.html')
            
            elif user_type == 'borrower':
                # Check if user is actually a borrower (not a company)
                try:
                    company = Company.objects.get(user=user)
                    # If company exists, this user is a lender, not a borrower
                    messages.error(request, 'This account is registered as a lending company. Please select "Lender" as your account type.')
                    return render(request, 'LoginApp/userLogin.html')
                    
                except Company.DoesNotExist:
                    # No company profile means this is a borrower
                    login(request, user)
                    
                    # Handle remember me
                    if not remember_me:
                        request.session.set_expiry(0)
                    
                    messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                    return redirect('borrower-dashboard')  # Redirect to borrower dashboard
            
            else:
                messages.error(request, 'Please select a valid account type.')
                return render(request, 'LoginApp/userLogin.html')
        
        else:
            messages.error(request, 'Invalid username/email or password.')
            return render(request, 'LoginApp/userLogin.html')
    
    # GET request - show login form
    return render(request, 'LoginApp/userLogin.html')

#Borrower logout function
def userLogout(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "You have been logged out successfully.")
    return redirect('user-login')

#Company logout function
def companyLogout(request):
    if request.user.is_authenticated:
        # Check if user is a company before logging out
        if hasattr(request.user, 'company_profile'):
            company_name = request.user.company_profile.company_name
            logout(request)
            messages.success(request, f"Goodbye {company_name}! You have been logged out successfully.")
        else:
            logout(request)
            messages.success(request, "You have been logged out successfully.")
    
    return redirect('landing-page')  # Redirect to login page