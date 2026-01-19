from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from decorators.auth_decorators import anonymous_required


@anonymous_required
def userLogin(request):
    """
    Login view - ONLY for Company users
    Borrowers don't need to login - they apply directly
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not username or not password:
            messages.error(request, 'Please provide both username/email and password.')
            return render(request, 'LoginApp/userLogin.html')
        
        # Try to authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # ONLY allow company users to login
            if hasattr(user, 'company_profile'):
                # Check if company is approved
                if user.company_profile.is_approved:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.company_profile.company_name}!')
                    return redirect('company-dashboard')
                else:
                    messages.error(request, 'Your company registration is pending approval. Please check back later.')
            else:
                messages.error(request, 'This login is only for registered lending companies. Borrowers can apply directly without an account.')
        else:
            messages.error(request, 'Invalid username/email or password. Please try again.')
    
    return render(request, 'LoginApp/userLogin.html')


@login_required
def userLogout(request):
    """
    Logout view - Only for authenticated company users
    """
    if hasattr(request.user, 'company_profile'):
        company_name = request.user.company_profile.company_name
        logout(request)
        messages.success(request, f'{company_name} has been logged out successfully.')
    else:
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
    
    return redirect('landing-page')


# Alias for company logout (same as userLogout)
def companyLogout(request):
    """Company-specific logout (redirects to userLogout)"""
    return userLogout(request)


@anonymous_required
def passwordResetRequest(request):
    """Handle password reset request - ONLY for company accounts"""
    if request.method == 'POST':
        email_or_username = request.POST.get('email_or_username', '').strip()
        
        if not email_or_username:
            messages.error(request, 'Please provide your email or username.')
            return render(request, 'LoginApp/passwordResetRequest.html')
        
        # Find user by email or username
        user = None
        try:
            user = User.objects.get(email=email_or_username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username=email_or_username)
            except User.DoesNotExist:
                pass
        
        if not user:
            messages.error(request, 'No company account found with that email/username.')
            return render(request, 'LoginApp/passwordResetRequest.html')
        
        # Verify user is a company (not borrower)
        if not hasattr(user, 'company_profile'):
            messages.error(request, 'This account is not registered as a lending company.')
            return render(request, 'LoginApp/passwordResetRequest.html')
        
        # Generate token and send email
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        reset_url = f"{settings.SITE_URL}/Auth/reset-password/{uid}/{token}/"
        
        subject = 'Password Reset Request - Avendro Company Portal'
        message = f"""
Hello {user.company_profile.company_name},

You requested to reset your password for your Avendro company account.

Click the link below to reset your password:
{reset_url}

This link will expire in 24 hours.

If you didn't request this, please ignore this email and your password will remain unchanged.

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
            messages.error(request, f'Failed to send email. Please try again later.')
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
    
    # Verify token and user is a company
    if user is not None and default_token_generator.check_token(user, token):
        # Double-check user is a company
        if not hasattr(user, 'company_profile'):
            messages.error(request, 'Invalid account type.')
            return redirect('user-login')
        
        if request.method == 'POST':
            new_password = request.POST.get('new_password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()
            
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