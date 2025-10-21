from decorators.auth_decorators import company_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import JsonResponse
import json
from BorrowerApp.models import Borrower
from CompanyApp.models import Company, LoanApplication, Notification
from django.utils import timezone
from django.db.models import Count, Avg, Q
import datetime
from django.db import models
from django.core.paginator import Paginator

@company_required
def companyDashboard(request):
    company = request.user.company_profile
    total_applicants = Borrower.objects.filter(is_active=True).count()
    active_loans = 0
    total_disbursed = 0
    default_rate = 0

    # Fetch recent applications for this company
    recent_applications = LoanApplication.objects.filter(company=company).order_by('-created_at')[:5]
    notifications = Notification.objects.filter(company=company).order_by('-created_at')[:5]

    # --- Monthly Performance Summary ---
    today = timezone.now()
    month_start = today.replace(day=1)
    applications_this_month = LoanApplication.objects.filter(
        company=company,
        created_at__gte=month_start
    )
    total_this_month = applications_this_month.count()
    approved_this_month = applications_this_month.filter(status='approved').count()
    approval_rate = round((approved_this_month / total_this_month * 100), 2) if total_this_month else 0

    # Average Processing Time (days)
    approved_apps = applications_this_month.filter(status='approved', approved_date__isnull=False)
    avg_processing = approved_apps.annotate(
        proc_time=(
            models.ExpressionWrapper(
                models.F('approved_date') - models.F('created_at'),
                output_field=models.DurationField()
            )
        )
    ).aggregate(avg_days=Avg('proc_time'))
    avg_days = avg_processing['avg_days'].days if avg_processing['avg_days'] else 0
    avg_days = round(avg_days, 1)

    # Satisfaction Score
    satisfaction_score = applications_this_month.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    satisfaction_score = round(satisfaction_score, 1)

    context = {
        'total_applicants': total_applicants,
        'active_loans': active_loans,
        'total_disbursed': total_disbursed,
        'default_rate': default_rate,
        'recent_applications': recent_applications,
        'notifications': notifications,
        'approval_rate': approval_rate,
        'avg_days': avg_days,
        'satisfaction_score': satisfaction_score,
    }
    return render(request, 'CompanyPages/companyDashboard.html', context)

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



@company_required
def loanApplication(request):
    company = request.user.company_profile

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')
    amount = request.GET.get('amount', '')

    # Base queryset
    applications_qs = LoanApplication.objects.filter(company=company).select_related('borrower')

    # Search by name, email, or amount
    if search:
        applications_qs = applications_qs.filter(
            Q(borrower__full_name__icontains=search) |
            Q(borrower__user__email__icontains=search) |
            Q(amount__icontains=search)
        )

    # Filter by status
    if status:
        applications_qs = applications_qs.filter(status=status)

    # Filter by amount range
    if amount:
        if amount == '0-10000':
            applications_qs = applications_qs.filter(amount__gte=0, amount__lte=10000)
        elif amount == '10000-50000':
            applications_qs = applications_qs.filter(amount__gt=10000, amount__lte=50000)
        elif amount == '50000-100000':
            applications_qs = applications_qs.filter(amount__gt=50000, amount__lte=100000)
        elif amount == '100000+':
            applications_qs = applications_qs.filter(amount__gt=100000)

    # Statistics (use filtered queryset for count if you want)
    total_applications = LoanApplication.objects.filter(company=company).count()
    pending_review = LoanApplication.objects.filter(company=company, status='pending').count()
    approved = LoanApplication.objects.filter(company=company, status='approved').count()
    total_amount = LoanApplication.objects.filter(company=company).aggregate(total=models.Sum('amount'))['total'] or 0

    # Pagination
    paginator = Paginator(applications_qs.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'total_applications': total_applications,
        'pending_review': pending_review,
        'approved': approved,
        'total_amount': total_amount,
        'page_obj': page_obj,
        'applications': page_obj.object_list,
        'paginator': paginator,
        'search': search,
        'status': status,
        'amount': amount,
    }
    return render(request, 'CompanyPages/companyLoanApplications.html', context)

def borrowerLists(request):
    return render(request, 'CompanyPages/companyBorrowerLists.html')

def activeLoans(request):
    return render(request, 'CompanyPages/companyActiveLoans.html')

def reports(request):
    return render(request, 'CompanyPages/companyReports.html')

def settings(request):
    return render(request, 'CompanyPages/companySettings.html')
