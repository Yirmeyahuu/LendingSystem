from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from BorrowerApp.models import Borrower
from CompanyApp.models import LoanApplication, Company
from decimal import Decimal, InvalidOperation
from datetime import datetime
import re
from decorators.auth_decorators import anonymous_required


#Landing Page Content function
@anonymous_required
def landingPage(request):
    return render(request, 'LandingPage/landing-page.html')


#Registration of Company function
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
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_active=True
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
                    
                    # Step 3: Compliance (renumbered from Step 4)
                    terms_accepted=request.POST.get('terms_accepted') == 'on',
                    compliance_accepted=request.POST.get('compliance_accepted') == 'on',
                    marketing_consent=request.POST.get('marketing_consent') == 'on',
                )
                
                messages.success(
                    request, 
                    'Registration successful! You are redirected to the login page. Please sign in to your account.'
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

#Company Success Registration function
def companyRegistrationSuccess(request):
    return render(request, 'CompanyRegistration/registerSuccess.html')