from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from CompanyApp.models import Company
from decorators.auth_decorators import anonymous_required
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from BorrowerApp.models import Borrower


#User login (Borrower or Company) Login function
@anonymous_required
def userLogin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_type = request.POST.get('user_type')
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
            messages.success(request, f"{company_name} have been logged out successfully.")
        else:
            logout(request)
            messages.success(request, "You have been logged out successfully.")
    
    return redirect('landing-page')

@anonymous_required
def passwordResetRequest(request):
    """Handle password reset request"""
    if request.method == 'POST':
        email_or_username = request.POST.get('email_or_username', '').strip()
        user_type = request.POST.get('user_type')
        
        if not email_or_username or not user_type:
            messages.error(request, 'Please provide email/username and select account type.')
            return render(request, 'LoginApp/passwordResetRequest.html')
        
        # Find user by email or username
        try:
            user = User.objects.get(email=email_or_username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username=email_or_username)
            except User.DoesNotExist:
                messages.error(request, 'No account found with that email/username.')
                return render(request, 'LoginApp/passwordResetRequest.html')
        
        # Verify user type matches
        if user_type == 'lender':
            if not hasattr(user, 'company_profile'):
                messages.error(request, 'This account is not registered as a lender.')
                return render(request, 'LoginApp/passwordResetRequest.html')
        elif user_type == 'borrower':
            if not hasattr(user, 'borrower_profile'):
                messages.error(request, 'This account is not registered as a borrower.')
                return render(request, 'LoginApp/passwordResetRequest.html')
        
        # Generate token and send email
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        reset_url = f"{settings.SITE_URL}/Auth/reset-password/{uid}/{token}/"
        
        subject = 'Password Reset Request - Avendro'
        message = f"""
Hello {user.first_name or user.username},

You requested to reset your password for your Avendro account.

Click the link below to reset your password:
{reset_url}

This link will expire in 24 hours.

If you didn't request this, please ignore this email.

Best regards,
Avendro Team
"""
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            messages.success(request, 'Password reset instructions have been sent to your email.')
            return redirect('user-login')
        except Exception as e:
            messages.error(request, f'Failed to send email: {str(e)}')
            return render(request, 'LoginApp/passwordResetRequest.html')
    
    return render(request, 'LoginApp/passwordResetRequest.html')


@anonymous_required
def passwordResetConfirm(request, uidb64, token):
    """Handle password reset confirmation"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Verify token
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Validate passwords
            if not new_password or not confirm_password:
                messages.error(request, 'Please fill in all fields.')
                return render(request, 'LoginApp/passwordResetConfirm.html', {'validlink': True})
            
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'LoginApp/passwordResetConfirm.html', {'validlink': True})
            
            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                return render(request, 'LoginApp/passwordResetConfirm.html', {'validlink': True})
            
            # Update password
            user.set_password(new_password)
            user.save()
            
            messages.success(request, 'Your password has been reset successfully. You can now login with your new password.')
            return redirect('user-login')
        
        return render(request, 'LoginApp/passwordResetConfirm.html', {'validlink': True})
    else:
        messages.error(request, 'This password reset link is invalid or has expired.')
        return render(request, 'LoginApp/passwordResetConfirm.html', {'validlink': False})