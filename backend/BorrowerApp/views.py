from decorators.auth_decorators import borrower_required 
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from .models import Borrower
from decimal import Decimal, InvalidOperation
from datetime import datetime
import re
from CompanyApp.models import LoanApplication

@borrower_required
def borrowerDashboard(request):
    borrower = request.user.borrower_profile

    # Get active loan (assuming status='approved' means active)
    active_loan = LoanApplication.objects.filter(borrower=borrower, status='approved').order_by('-created_at').first()

    # Example payment logic (replace with your actual payment model/logic)
    next_payment = None
    due_date = None
    outstanding_balance = None
    if active_loan:
        outstanding_balance = active_loan.amount  # Replace with actual balance calculation if you track payments
        # If you have a Payment model, get the next due payment
        payment = getattr(active_loan, 'next_payment', None)
        if payment:
            next_payment = payment.amount
            due_date = payment.due_date
        else:
            next_payment = 0
            due_date = None

    # Borrower status badge
    status = "Active" if borrower.is_active else "Inactive"

    context = {
        'active_loan': active_loan,
        'outstanding_balance': outstanding_balance,
        'next_payment': next_payment,
        'due_date': due_date,
        'status': status,
    }
    return render(request, 'BorrowerPages/borrowerDashboard.html', context)

def borrower_logout(request):
    if request.user.is_authenticated:
        # Check if user is a borrower before logging out
        if hasattr(request.user, 'borrower_profile'):
            user_name = request.user.borrower_profile.first_name
            logout(request)
            messages.success(request, f"Goodbye {user_name}! You have been logged out successfully.")
        else:
            logout(request)
            messages.success(request, "You have been logged out successfully.")
    
    return redirect('landing-page')  # Redirect to login page

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

def borrowerRegistrationSuccess(request):
    return render(request, 'RegistrationSuccess/borrowerSuccess.html')


@borrower_required
def activeLoans(request):
    borrower = request.user.borrower_profile
    active_loans = LoanApplication.objects.filter(borrower=borrower, status='approved').order_by('-created_at')

    context = {
        'active_loans': active_loans,
    }
    return render(request, 'MyLoanSubmenus/activeLoans.html', context)

@borrower_required
def loanHistory(request):
    borrower = request.user.borrower_profile
    loan_history = LoanApplication.objects.filter(borrower=borrower).order_by('-created_at')

    context = {
        'loan_history': loan_history,
    }
    return render(request, 'MyLoanSubmenus/loanHistory.html', context)

@borrower_required
def applyLoan(request):
    borrower = request.user.borrower_profile
    from CompanyApp.models import Company, LoanApplication

    # Get all approved companies/lenders
    companies = Company.objects.filter(is_approved=True)

    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        product_type = request.POST.get('product_type')
        amount = request.POST.get('amount')
        # Handle document uploads
        income_doc = request.FILES.get('income_doc')
        payslip_doc = request.FILES.get('payslip_doc')

        # Basic validation
        errors = []
        if not company_id:
            errors.append("Please select a lender.")
        if not product_type:
            errors.append("Please select a loan product.")
        if not amount:
            errors.append("Please enter a loan amount.")

        try:
            amount = Decimal(amount)
            if amount <= 0:
                errors.append("Loan amount must be greater than zero.")
        except Exception:
            errors.append("Invalid loan amount.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'ApplyLoan/applyLoan.html', {'companies': companies})

        # Get selected company
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            messages.error(request, "Selected lender does not exist.")
            return render(request, 'ApplyLoan/applyLoan.html', {'companies': companies})

        # Create LoanApplication
        loan = LoanApplication.objects.create(
            borrower=borrower,
            company=company,
            product_type=product_type,
            amount=amount,
            status='pending'
        )
        # Handle document uploads (save to loan or another model as needed)
        # Example: loan.income_doc = income_doc; loan.payslip_doc = payslip_doc

        messages.success(request, "Your loan application has been submitted and is now pending review.")
        return redirect('borrower-apply-loan')

    return render(request, 'ApplyLoan/applyLoan.html', {'companies': companies})


@borrower_required
def borrowerPayments(request):
    borrower = request.user.borrower_profile
    from CompanyApp.models import LoanApplication, Payment

    # Get all payments for borrower's approved loans
    payments = Payment.objects.filter(loan_application__borrower=borrower).order_by('-due_date')

    context = {
        'payments': payments,
    }
    return render(request, 'Payments/borrowerPayment.html', context)


@borrower_required
def borrowerProfile(request):
    borrower = request.user.borrower_profile

    if request.method == 'POST':
        # Update profile logic here
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        mobile_number = request.POST.get('mobile_number', '').strip()
        # Add more fields as necessary

        # Basic validation
        if not first_name or not last_name or not mobile_number:
            messages.error(request, "First name, last name, and mobile number are required.")
            return render(request, 'Profile/borrowerProfile.html', {'borrower': borrower})

        # Update borrower profile
        borrower.first_name = first_name
        borrower.last_name = last_name
        borrower.mobile_number = mobile_number
        # Update more fields as necessary
        borrower.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('borrower-profile')

    return render(request, 'Profile/borrowerProfile.html', {'borrower': borrower})

@borrower_required
def update_security_questions(request):
    borrower = request.user.borrower_profile
    if request.method == 'POST':
        borrower.security_question_1 = request.POST.get('security_question_1', '').strip()
        borrower.security_answer_1 = request.POST.get('security_answer_1', '').strip()
        borrower.security_question_2 = request.POST.get('security_question_2', '').strip()
        borrower.security_answer_2 = request.POST.get('security_answer_2', '').strip()
        borrower.save()
        messages.success(request, "Security questions updated successfully.")
        return redirect('borrower-profile')
    return redirect('borrower-profile')

@borrower_required
def changePassword(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.user

        # Validate current password
        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('borrower-change-password')

        # Validate new password match
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('borrower-change-password')

        # Validate new password strength
        if len(new_password) < 8:
            messages.error(request, "New password must be at least 8 characters long.")
            return redirect('borrower-change-password')

        # Update password
        user.set_password(new_password)
        user.save()
        messages.success(request, "Password changed successfully. Please log in again.")
        return redirect('login')

    return render(request, 'Profile/changePassword.html')