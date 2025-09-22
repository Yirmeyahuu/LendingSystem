from decorators.auth_decorators import company_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import JsonResponse
import json
from .models import Company



# Create your views here.
@company_required
def companyDashboard(request):
    return render(request, 'CompanyPages/companyDashboard.html')

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

def companyRegistration(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Extract login credentials
                username = request.POST.get('username')
                email = request.POST.get('email')
                password = request.POST.get('password')
                confirm_password = request.POST.get('confirm_password')
                
                # Validate passwords match
                if password != confirm_password:
                    messages.error(request, 'Passwords do not match.')
                    return render(request, 'CompanyRegistration/registerCompany.html')
                
                # Check if username or email already exists
                if User.objects.filter(username=username).exists():
                    messages.error(request, 'Username already exists.')
                    return render(request, 'CompanyRegistration/registerCompany.html')
                
                if User.objects.filter(email=email).exists():
                    messages.error(request, 'Email address already registered.')
                    return render(request, 'CompanyRegistration/registerCompany.html')
                
                # Create User instance
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_active=False  # Will be activated after admin approval
                )
                
                # Process loan products (checkbox values)
                loan_products = request.POST.getlist('loan_products')
                if not loan_products:
                    messages.error(request, 'Please select at least one loan product.')
                    user.delete()  # Clean up created user
                    return render(request, 'CompanyRegistration/registerCompany.html')
                
                # Process optional fields
                processing_fee = request.POST.get('processing_fee')
                if processing_fee == '':
                    processing_fee = None
                
                late_payment_fee = request.POST.get('late_payment_fee')
                if late_payment_fee == '':
                    late_payment_fee = None
                
                swift_code = request.POST.get('swift_code')
                if swift_code == '':
                    swift_code = None
                
                website = request.POST.get('website')
                if website == '':
                    website = None
                
                # Create Company instance
                company = Company.objects.create(
                    user=user,
                    # Step 1: Company Information
                    company_name=request.POST.get('company_name'),
                    registration_number=request.POST.get('registration_number'),
                    tax_id=request.POST.get('tax_id'),
                    street_address=request.POST.get('street_address'),
                    city=request.POST.get('city'),
                    state=request.POST.get('state'),
                    postal_code=request.POST.get('postal_code'),
                    contact_person=request.POST.get('contact_person'),
                    contact_title=request.POST.get('contact_title'),
                    company_phone=request.POST.get('company_phone'),
                    business_email=request.POST.get('business_email'),
                    website=website,
                    
                    # Step 2: Loan Products & Operations
                    loan_products=loan_products,
                    min_loan_amount=request.POST.get('min_loan_amount'),
                    max_loan_amount=request.POST.get('max_loan_amount'),
                    min_interest_rate=request.POST.get('min_interest_rate'),
                    max_interest_rate=request.POST.get('max_interest_rate'),
                    processing_fee=processing_fee,
                    late_payment_fee=late_payment_fee,
                    min_loan_term=request.POST.get('min_loan_term'),
                    max_loan_term=request.POST.get('max_loan_term'),
                    lending_policies=request.POST.get('lending_policies'),
                    
                    # Step 3: Banking Information
                    bank_name=request.POST.get('bank_name'),
                    account_holder_name=request.POST.get('account_holder_name'),
                    account_number=request.POST.get('account_number'),
                    routing_number=request.POST.get('routing_number'),
                    account_type=request.POST.get('account_type'),
                    swift_code=swift_code,
                    monthly_volume=request.POST.get('monthly_volume'),
                    years_in_business=request.POST.get('years_in_business'),
                    
                    # Step 4: Compliance
                    terms_accepted=request.POST.get('terms_accepted') == 'on',
                    compliance_accepted=request.POST.get('compliance_accepted') == 'on',
                    marketing_consent=request.POST.get('marketing_consent') == 'on',
                )
                
                messages.success(
                    request, 
                    'Registration successful! Your application is under review. '
                    'You will receive an email notification once your account is approved.'
                )
                
                # Redirect to a success page or login page
                return redirect('company-registration-success')  # You'll need to create this URL
                
        except ValidationError as e:
            messages.error(request, f'Validation error: {e.message}')
            return render(request, 'CompanyRegistration/registerCompany.html')
        
        except Exception as e:
            messages.error(request, f'An error occurred during registration: {str(e)}')
            return render(request, 'CompanyRegistration/registerCompany.html')
    
    # GET request - display the registration form
    return render(request, 'CompanyRegistration/registerCompany.html')

def companyRegistrationSuccess(request):
    return render(request, 'RegistrationSuccess/registrationSuccess.html')

def loanApplication(request):
    return render(request, 'CompanyPages/companyLoanApplications.html')

def borrowerLists(request):
    return render(request, 'CompanyPages/companyBorrowerLists.html')

def activeLoans(request):
    return render(request, 'CompanyPages/companyActiveLoans.html')

def reports(request):
    return render(request, 'CompanyPages/companyReports.html')

def settings(request):
    return render(request, 'CompanyPages/companySettings.html')