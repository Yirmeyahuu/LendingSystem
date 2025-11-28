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

#Registration of Borrower function
def registerBorrower(request):
    if request.method == 'POST':
        try:
            # Extract form data
            form_data = request.POST
            
            # Validate required fields
            required_fields = [
                'first_name', 'last_name', 'date_of_birth', 'gender', 'marital_status',
                'mobile_number', 'current_street_address', 'current_city', 'current_state',
                'current_postal_code', 'employment_status', 'monthly_income', 'income_source',
                'bank_name', 'account_number', 'username', 'email', 'password', 'confirm_password'
            ]
            
            # Check if all required fields are filled
            missing_fields = []
            for field in required_fields:
                if not form_data.get(field, '').strip():
                    missing_fields.append(field.replace('_', ' ').title())
            
            if missing_fields:
                messages.error(request, f"Please fill in all required fields: {', '.join(missing_fields)}")
                return render(request, 'BorrowerRegistration/registerBorrower.html')
            
            # Validate password match
            password = form_data.get('password')
            confirm_password = form_data.get('confirm_password')
            
            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, 'BorrowerRegistration/registerBorrower.html')
            
            # Validate password strength
            if len(password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return render(request, 'BorrowerRegistration/registerBorrower.html')
            
            # Validate email format
            email = form_data.get('email').strip().lower()
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                messages.error(request, "Please enter a valid email address.")
                return render(request, 'BorrowerRegistration/registerBorrower.html')
            
            # Validate username
            username = form_data.get('username').strip()
            if len(username) < 3 or len(username) > 20:
                messages.error(request, "Username must be between 3 and 20 characters.")
                return render(request, 'BorrowerRegistration/registerBorrower.html')
            
            # Validate monthly income
            try:
                monthly_income = Decimal(form_data.get('monthly_income'))
                if monthly_income < 0:
                    messages.error(request, "Monthly income cannot be negative.")
                    return render(request, 'BorrowerRegistration/registerBorrower.html')
            except (InvalidOperation, ValueError):
                messages.error(request, "Please enter a valid monthly income amount.")
                return render(request, 'BorrowerRegistration/registerBorrower.html')
            
            # Validate date of birth
            try:
                date_of_birth = datetime.strptime(form_data.get('date_of_birth'), '%Y-%m-%d').date()
                today = datetime.now().date()
                age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
                
                if age < 18:
                    messages.error(request, "You must be at least 18 years old to register.")
                    return render(request, 'BorrowerRegistration/registerBorrower.html')
                
                if age > 100:
                    messages.error(request, "Please enter a valid date of birth.")
                    return render(request, 'BorrowerRegistration/registerBorrower.html')
                    
            except ValueError:
                messages.error(request, "Please enter a valid date of birth.")
                return render(request, 'BorrowerRegistration/registerBorrower.html')
            
            # Validate terms acceptance
            if not form_data.get('terms_accepted'):
                messages.error(request, "You must accept the Terms of Service and Privacy Policy.")
                return render(request, 'BorrowerRegistration/registerBorrower.html')
            
            # Handle employment fields based on status
            employment_status = form_data.get('employment_status')
            company_name = form_data.get('company_name', '').strip()
            job_title = form_data.get('job_title', '').strip()
            
            if employment_status in ['employed', 'self_employed']:
                if not company_name or not job_title:
                    messages.error(request, "Company name and job title are required for employed/self-employed status.")
                    return render(request, 'BorrowerRegistration/registerBorrower.html')
            
            # Handle permanent address
            permanent_street_address = form_data.get('permanent_street_address', '').strip()
            permanent_city = form_data.get('permanent_city', '').strip()
            permanent_state = form_data.get('permanent_state', '').strip()
            permanent_postal_code = form_data.get('permanent_postal_code', '').strip()
            
            # If permanent address is not provided, use current address
            if not permanent_street_address:
                permanent_street_address = form_data.get('current_street_address')
                permanent_city = form_data.get('current_city')
                permanent_state = form_data.get('current_state')
                permanent_postal_code = form_data.get('current_postal_code')
            
            # Use database transaction to ensure data integrity
            with transaction.atomic():
                # Check if username or email already exists
                if User.objects.filter(username=username).exists():
                    messages.error(request, "Username already exists. Please choose a different username.")
                    return render(request, 'BorrowerRegistration/registerBorrower.html')
                
                if User.objects.filter(email=email).exists():
                    messages.error(request, "Email address already registered. Please use a different email.")
                    return render(request, 'BorrowerRegistration/registerBorrower.html')
                
                # Create User instance with hashed password
                user = User.objects.create(
                    username=username,
                    email=email,
                    password=make_password(password),  # Hash the password
                    first_name=form_data.get('first_name').strip(),
                    last_name=form_data.get('last_name').strip(),
                    is_active=True
                )
                
                # Create Borrower instance
                borrower = Borrower.objects.create(
                    user=user,
                    # Personal Information
                    first_name=form_data.get('first_name').strip(),
                    middle_name=form_data.get('middle_name', '').strip() or None,
                    last_name=form_data.get('last_name').strip(),
                    date_of_birth=date_of_birth,
                    gender=form_data.get('gender'),
                    marital_status=form_data.get('marital_status'),
                    
                    # Contact Information
                    mobile_number=form_data.get('mobile_number').strip(),
                    
                    # Current Address
                    current_street_address=form_data.get('current_street_address').strip(),
                    current_city=form_data.get('current_city').strip(),
                    current_state=form_data.get('current_state').strip(),
                    current_postal_code=form_data.get('current_postal_code').strip(),
                    
                    # Permanent Address
                    permanent_street_address=permanent_street_address,
                    permanent_city=permanent_city,
                    permanent_state=permanent_state,
                    permanent_postal_code=permanent_postal_code,
                    
                    # Employment and Financial Information
                    employment_status=employment_status,
                    company_name=company_name or None,
                    job_title=job_title or None,
                    monthly_income=monthly_income,
                    income_source=form_data.get('income_source').strip(),
                    
                    # Bank Account Details
                    bank_name=form_data.get('bank_name').strip(),
                    account_number=form_data.get('account_number').strip(),
                    
                    # Consent and Agreement fields
                    terms_accepted=True,  # Already validated above
                    marketing_consent=bool(form_data.get('marketing_consent')),
                    
                    # Set initial status
                    is_verified=False,
                    is_active=True
                )
                
                messages.success(
                    request, 
                    'Registration successful! Your application is under review. '
                    'You will receive an email notification once your account is approved.'
                )
                
                # Redirect to a success page or login page
                return redirect('borrower-registration-success')
                
        except IntegrityError as e:
            messages.error(request, "Registration failed due to a database error. Please try again.")
            return render(request, 'BorrowerRegistration/registerBorrower.html')
            
        except ValidationError as e:
            messages.error(request, f"Validation error: {str(e)}")
            return render(request, 'BorrowerRegistration/registerBorrower.html')
        except Exception as e:
            messages.error(request, "An unexpected error occurred. Please try again.")
            return render(request, 'BorrowerRegistration/registerBorrower.html')
    
    # GET request - display the registration form
    return render(request, 'BorrowerRegistration/registerBorrower.html')

#Borrower Success Registration function
def borrowerRegistrationSuccess(request):
    return render(request, 'RegistrationSuccess/borrowerSuccess.html')

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
    return render(request, 'RegistrationSuccess/registrationSuccess.html')