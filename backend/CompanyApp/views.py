from decorators.auth_decorators import company_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.http import JsonResponse
import json
from BorrowerApp.models import Borrower
from CompanyApp.models import Company, LoanApplication, Notification
from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum
from datetime import datetime, timedelta, date
from django.db import models
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.hashers import make_password
from decimal import Decimal, InvalidOperation
import re



#Company Dashboard function
@company_required
def companyDashboard(request):
    company = request.user.company_profile
    total_applications = LoanApplication.objects.filter(company=company).count()
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
        'total_applications': total_applications,
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


#Company Loan Application function
@company_required
def loanApplication(request):
    company = request.user.company_profile

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')
    amount = request.GET.get('amount', '')

    # Base queryset - Exclude rejected by default unless specifically filtered
    if status == 'rejected':
        applications_qs = LoanApplication.objects.filter(company=company, status='rejected').select_related('borrower')
    else:
        applications_qs = LoanApplication.objects.filter(company=company).exclude(status='rejected').select_related('borrower')

    # Search by name, email, or amount
    if search:
        applications_qs = applications_qs.filter(
            Q(borrower__full_name__icontains=search) |
            Q(borrower__user__email__icontains=search) |
            Q(amount__icontains=search)
        )

    # Filter by status (if not rejected, since we handled that above)
    if status and status != 'rejected':
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

    # Statistics (exclude rejected from counts)
    total_applications = LoanApplication.objects.filter(company=company).exclude(status='rejected').count()
    pending_review = LoanApplication.objects.filter(company=company, status='pending').count()
    approved = LoanApplication.objects.filter(company=company, status='approved').count()
    rejected = LoanApplication.objects.filter(company=company, status='rejected').count()
    total_amount = LoanApplication.objects.filter(
        company=company, 
        status='approved'
    ).aggregate(total=models.Sum('amount'))['total'] or 0

    # Pagination
    paginator = Paginator(applications_qs.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'total_applications': total_applications,
        'pending_review': pending_review,
        'approved': approved,
        'rejected': rejected,
        'total_amount': total_amount,
        'page_obj': page_obj,
        'applications': page_obj.object_list,
        'paginator': paginator,
        'search': search,
        'status': status,
        'amount': amount,
    }
    return render(request, 'CompanyPages/companyLoanApplications.html', context)


# View Loan Application Details (AJAX)
@company_required
def viewLoanApplication(request, application_id):
    """
    Return loan application details as JSON for modal display
    """
    try:
        company = request.user.company_profile
        application = get_object_or_404(
            LoanApplication.objects.select_related('borrower__user'),
            id=application_id,
            company=company
        )
        
        borrower = application.borrower
        
        # Format addresses safely
        current_address = None
        if borrower.current_street_address:
            current_address = f"{borrower.current_street_address}, {borrower.current_city}, {borrower.current_state} {borrower.current_postal_code}"
        
        permanent_address = None
        if borrower.permanent_street_address:
            permanent_address = f"{borrower.permanent_street_address}, {borrower.permanent_city}, {borrower.permanent_state} {borrower.permanent_postal_code}"
        
        data = {
            'success': True,
            'application': {
                'id': application.id,
                'status': application.status,
                'amount': str(application.amount),
                'product_type': getattr(application, 'product_type', 'Personal Loan'),
                'purpose': getattr(application, 'purpose', 'Not specified'),
                'term': getattr(application, 'term', None),
                'interest_rate': str(application.interest_rate) if hasattr(application, 'interest_rate') and application.interest_rate else None,
                'created_at': application.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'borrower': {
                    'full_name': borrower.full_name,
                    'email': borrower.user.email,
                    'mobile_number': borrower.mobile_number or 'Not provided',
                    'date_of_birth': borrower.date_of_birth.strftime('%B %d, %Y') if borrower.date_of_birth else 'Not provided',
                    'gender': borrower.gender or 'Not specified',
                    'marital_status': borrower.marital_status or 'Not specified',
                    'current_address': current_address or 'Not provided',
                    'permanent_address': permanent_address or 'Not provided',
                    'employment_status': borrower.employment_status or 'Not specified',
                    'company_name': borrower.company_name or None,
                    'job_title': borrower.job_title or None,
                    'monthly_income': str(borrower.monthly_income) if borrower.monthly_income else '0',
                    'income_source': borrower.income_source or 'Not specified',
                    'bank_name': borrower.bank_name or None,
                    'account_number': borrower.account_number or None,
                }
            }
        }
        
        return JsonResponse(data)
        
    except LoanApplication.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Loan application not found.'
        }, status=404)
    except AttributeError as e:
        return JsonResponse({
            'success': False,
            'message': f'Missing attribute: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


#Company Borrower List Function
@company_required
def borrowerLists(request):
    company = request.user.company_profile

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')
    risk = request.GET.get('risk', '')

    # Base queryset - Only borrowers with approved loans from this company
    borrowers_qs = Borrower.objects.filter(
        loanapplication__company=company,
        loanapplication__status='approved'
    ).distinct()

    # Annotate outstanding amount for this company only
    borrowers_qs = borrowers_qs.annotate(
        outstanding_amount=Sum(
            'loanapplication__amount',
            filter=Q(loanapplication__company=company, loanapplication__status='approved')
        )
    )

    # Search by name or email
    if search:
        borrowers_qs = borrowers_qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(user__email__icontains=search)
        )

    # Filter by status
    if status:
        if status == 'active':
            borrowers_qs = borrowers_qs.filter(is_active=True)
        elif status == 'inactive':
            borrowers_qs = borrowers_qs.filter(is_active=False)
        elif status == 'delinquent':
            borrowers_qs = borrowers_qs.filter(
                loanapplication__company=company,
                loanapplication__status='delinquent'
            ).distinct()
        elif status == 'defaulted':
            borrowers_qs = borrowers_qs.filter(
                loanapplication__company=company,
                loanapplication__status='defaulted'
            ).distinct()

    # Filter by risk level (if you have a 'risk_level' field)
    if risk:
        borrowers_qs = borrowers_qs.filter(risk_level=risk)

    # Pagination
    paginator = Paginator(borrowers_qs.order_by('-updated_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate statistics for this company only
    total_borrowers = Borrower.objects.filter(
        loanapplication__company=company,
        loanapplication__status='approved'
    ).distinct().count()
    
    active_borrowers = Borrower.objects.filter(
        loanapplication__company=company,
        loanapplication__status='approved',
        is_active=True
    ).distinct().count()
    
    delinquent_borrowers = Borrower.objects.filter(
        loanapplication__company=company,
        loanapplication__status='delinquent'
    ).distinct().count()
    
    portfolio_value = LoanApplication.objects.filter(
        company=company,
        status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'total_borrowers': total_borrowers,
        'active_borrowers': active_borrowers,
        'delinquent_borrowers': delinquent_borrowers,
        'portfolio_value': portfolio_value,
        'search': search,
        'status': status,
        'risk': risk,
        'page_obj': page_obj,
        'borrowers': page_obj.object_list,
        'paginator': paginator,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        'start_index': page_obj.start_index(),
        'end_index': page_obj.end_index(),
    }
    return render(request, 'CompanyPages/companyBorrowerLists.html', context)

#Company Active Loans Function
@company_required
def activeLoans(request):
    company = request.user.company_profile

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    loan_type = request.GET.get('loanType', '')
    payment_status = request.GET.get('paymentStatus', '')
    amount_range = request.GET.get('amountRange', '')
    date_range = request.GET.get('dateRange', '')

    # Base queryset
    loans_qs = LoanApplication.objects.filter(company=company, status='approved')

    # Search by borrower name, loan ID, or amount
    if search:
        loans_qs = loans_qs.filter(
            Q(borrower__first_name__icontains=search) |
            Q(borrower__last_name__icontains=search) |
            Q(id__icontains=search) |
            Q(amount__icontains=search)
        )

    # Filter by loan type
    if loan_type:
        loans_qs = loans_qs.filter(product_type=loan_type)

    # Filter by payment status (maps to your status field)
    if payment_status:
        status_map = {
            'current': 'approved',
            'late': 'delinquent',
            'overdue': 'delinquent',  # adjust if you have a separate 'overdue'
            'grace': 'review',        # adjust if you have a separate 'grace'
        }
        mapped_status = status_map.get(payment_status)
        if mapped_status:
            loans_qs = loans_qs.filter(status=mapped_status)

    # Filter by amount range
    if amount_range:
        if amount_range == '0-25000':
            loans_qs = loans_qs.filter(amount__gte=0, amount__lte=25000)
        elif amount_range == '25000-100000':
            loans_qs = loans_qs.filter(amount__gt=25000, amount__lte=100000)
        elif amount_range == '100000-500000':
            loans_qs = loans_qs.filter(amount__gt=100000, amount__lte=500000)
        elif amount_range == '500000+':
            loans_qs = loans_qs.filter(amount__gt=500000)

    # Filter by date range
    if date_range:
        today = timezone.now().date()
        if date_range == 'last-30':
            start_date = today - datetime.timedelta(days=30)
            loans_qs = loans_qs.filter(created_at__gte=start_date)
        elif date_range == 'last-90':
            start_date = today - datetime.timedelta(days=90)
            loans_qs = loans_qs.filter(created_at__gte=start_date)
        elif date_range == 'last-year':
            start_date = today - datetime.timedelta(days=365)
            loans_qs = loans_qs.filter(created_at__gte=start_date)
        # For 'custom', you'd need to handle custom date inputs

    # Statistics
    total_active_loans = loans_qs.count()
    portfolio_value = loans_qs.aggregate(total=models.Sum('amount'))['total'] or 0

    # Loan Performance (same as before)
    on_time = loans_qs.filter(status='approved').count()
    late = loans_qs.filter(status='delinquent').count()
    missed = loans_qs.filter(status='defaulted').count() if 'defaulted' in dict(LoanApplication._meta.get_field('status').choices) else 0
    total_perf = on_time + late + missed
    on_time_pct = round((on_time / total_perf * 100), 1) if total_perf else 0
    late_pct = round((late / total_perf * 100), 1) if total_perf else 0
    missed_pct = round((missed / total_perf * 100), 1) if total_perf else 0

    # Loan Distribution by product_type
    product_types = dict(company.LOAN_PRODUCT_CHOICES)
    distribution = []
    for key, label in product_types.items():
        count = loans_qs.filter(product_type=key).count()
        amount = loans_qs.filter(product_type=key).aggregate(total=models.Sum('amount'))['total'] or 0
        percent = round((count / total_active_loans * 100), 1) if total_active_loans else 0
        distribution.append({
            'label': label,
            'count': count,
            'amount': amount,
            'percent': percent,
            'icon': key,
        })

    # Pagination
    paginator = Paginator(loans_qs.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'total_active_loans': total_active_loans,
        'portfolio_value': portfolio_value,
        'on_time_pct': on_time_pct,
        'late_pct': late_pct,
        'missed_pct': missed_pct,
        'distribution': distribution,
        'page_obj': page_obj,
        'loans': page_obj.object_list,
        'paginator': paginator,
        'search': search,
        'loan_type': loan_type,
        'payment_status': payment_status,
        'amount_range': amount_range,
        'date_range': date_range,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        'start_index': page_obj.start_index(),
        'end_index': page_obj.end_index(),
    }
    return render(request, 'CompanyPages/companyActiveLoans.html', context)

#Company Reports function
@company_required
def reports(request):
    company = request.user.company_profile

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    loan_type = request.GET.get('loanType', '')
    payment_status = request.GET.get('paymentStatus', '')
    amount_range = request.GET.get('amountRange', '')
    date_range = request.GET.get('dateRange', '')

    context = {
        'search': search,
        'loan_type': loan_type,
        'payment_status': payment_status,
        'amount_range': amount_range,
        'date_range': date_range,
    }

    return render(request, 'CompanyPages/companyReports.html', context)

#Company Settings function
@company_required
def settings(request):
    company = request.user.company_profile
    total_loans = LoanApplication.objects.filter(company=company).count()

    if request.method == 'POST':
        # Company Information
        company.company_name = request.POST.get('company_name', company.company_name)
        company.business_email = request.POST.get('business_email', company.business_email)
        company.company_phone = request.POST.get('company_phone', company.company_phone)
        company.website = request.POST.get('website', company.website)
        # For simplicity, this example updates the main street_address field.
        # You could expand this to update city, state, etc. if you add more fields to the form.
        company.street_address = request.POST.get('business_address', company.street_address)

        # Loan Settings
        company.min_interest_rate = request.POST.get('min_interest_rate', company.min_interest_rate)
        company.max_interest_rate = request.POST.get('max_interest_rate', company.max_interest_rate)
        company.min_loan_term = request.POST.get('min_loan_term', company.min_loan_term)
        company.max_loan_term = request.POST.get('max_loan_term', company.max_loan_term)
        company.late_payment_fee = request.POST.get('late_payment_fee', company.late_payment_fee)
        
        try:
            company.save()
            messages.success(request, 'Your settings have been updated successfully.')
        except ValidationError as e:
            messages.error(request, f"Error saving settings: {e}")
        
        return redirect('company-settings')

    context = {
        'company': company,
        'total_loans': total_loans,
    }
    return render(request, 'CompanyPages/companySettings.html', context)

#Company Active function
@company_required
def activeBorrowers(request):
    company = request.user.company_profile

    # Borrowers with at least one active loan
    active_borrowers_qs = Borrower.objects.filter(
        loanapplication__company=company,
        loanapplication__status='approved'
    ).distinct().annotate(
        active_loans_count=Count('loanapplication', filter=Q(loanapplication__company=company, loanapplication__status='approved'))
    )

    total_active_borrowers = active_borrowers_qs.count()
    total_loans = LoanApplication.objects.filter(company=company, status='approved').count()
    total_portfolio = LoanApplication.objects.filter(company=company, status='approved').aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'active_borrowers': active_borrowers_qs,
        'total_active_borrowers': total_active_borrowers,
        'total_loans': total_loans,
        'total_portfolio': total_portfolio,
    }
    return render(request, 'BorrowerSubmenus/companyActiveBorrowers.html', context)

#Company Potential Borrowers Function
@company_required
def potentialBorrowers(request):
    company = request.user.company_profile

    # Get borrowers who have pending applications with this company
    potential_borrowers = Borrower.objects.filter(
        loanapplication__company=company,
        loanapplication__status='pending'
    ).distinct().annotate(
        pending_applications_count=Count(
            'loanapplication',
            filter=Q(loanapplication__company=company, loanapplication__status='pending')
        )
    )

    # Statistics
    total_potential = potential_borrowers.count()
    total_pending_applications = LoanApplication.objects.filter(
        company=company,
        status='pending'
    ).count()
    total_requested_amount = LoanApplication.objects.filter(
        company=company,
        status='pending'
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'potential_borrowers': potential_borrowers,
        'total_potential': total_potential,
        'total_pending_applications': total_pending_applications,
        'total_requested_amount': total_requested_amount,
    }
    return render(request, 'BorrowerSubmenus/companyPotentialBorrowers.html', context)

#Company Archived Borrowers Function
@company_required
def archivedBorrowers(request):
    company = request.user.company_profile

    # Get borrowers who are inactive but have had loans with this company
    archived_borrowers = Borrower.objects.filter(
        loanapplication__company=company,
        is_active=False
    ).distinct().annotate(
        total_loans=Count(
            'loanapplication',
            filter=Q(loanapplication__company=company)
        ),
        total_borrowed=Sum(
            'loanapplication__amount',
            filter=Q(loanapplication__company=company, loanapplication__status='approved')
        )
    )

    # Statistics
    total_archived = archived_borrowers.count()
    total_historical_loans = LoanApplication.objects.filter(
        company=company,
        borrower__is_active=False
    ).count()

    context = {
        'archived_borrowers': archived_borrowers,
        'total_archived': total_archived,
        'total_historical_loans': total_historical_loans,
    }
    return render(request, 'BorrowerSubmenus/companyArchivedBorrowers.html', context)


#Company Add Borrower function
@company_required
def addBorrowers(request):
    company = request.user.company_profile

    if request.method == 'POST':
        try:
            form_data = request.POST
            
            # Validate required fields
            required_fields = [
                'first_name', 'last_name', 'date_of_birth', 'gender', 'marital_status',
                'mobile_number', 'current_street_address', 'current_city', 'current_state',
                'current_postal_code', 'employment_status', 'monthly_income', 'income_source',
                'bank_name', 'account_number', 'username', 'email', 'password', 'confirm_password'
            ]
            
            missing_fields = [field.replace('_', ' ').title() for field in required_fields 
                            if not form_data.get(field, '').strip()]
            
            if missing_fields:
                messages.error(request, f"Please fill in all required fields: {', '.join(missing_fields)}")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
            
            # Validate password match
            password = form_data.get('password')
            confirm_password = form_data.get('confirm_password')
            
            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
            
            if len(password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
            
            # Validate email
            email = form_data.get('email').strip().lower()
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                messages.error(request, "Please enter a valid email address.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
            
            # Validate username
            username = form_data.get('username').strip()
            if len(username) < 3 or len(username) > 20:
                messages.error(request, "Username must be between 3 and 20 characters.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
            
            # Validate monthly income
            try:
                monthly_income = Decimal(form_data.get('monthly_income'))
                if monthly_income < 0:
                    messages.error(request, "Monthly income cannot be negative.")
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
            except (InvalidOperation, ValueError):
                messages.error(request, "Please enter a valid monthly income amount.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
            
            # Validate date of birth
            try:
                date_of_birth = datetime.strptime(form_data.get('date_of_birth'), '%Y-%m-%d').date()
                today = datetime.now().date()
                age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
                
                if age < 18:
                    messages.error(request, "Borrower must be at least 18 years old.")
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
                
                if age > 100:
                    messages.error(request, "Please enter a valid date of birth.")
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
                    
            except ValueError:
                messages.error(request, "Please enter a valid date of birth.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
            
            # Handle employment fields
            employment_status = form_data.get('employment_status')
            company_name = form_data.get('company_name', '').strip()
            job_title = form_data.get('job_title', '').strip()
            
            if employment_status in ['employed', 'self_employed']:
                if not company_name or not job_title:
                    messages.error(request, "Company name and job title are required for employed/self-employed status.")
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
            
            # Handle permanent address
            permanent_street_address = form_data.get('permanent_street_address', '').strip()
            permanent_city = form_data.get('permanent_city', '').strip()
            permanent_state = form_data.get('permanent_state', '').strip()
            permanent_postal_code = form_data.get('permanent_postal_code', '').strip()
            
            if not permanent_street_address:
                permanent_street_address = form_data.get('current_street_address')
                permanent_city = form_data.get('current_city')
                permanent_state = form_data.get('current_state')
                permanent_postal_code = form_data.get('current_postal_code')
            
            # Use database transaction
            with transaction.atomic():
                # Check if username or email already exists
                if User.objects.filter(username=username).exists():
                    messages.error(request, "Username already exists. Please choose a different username.")
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
                
                if User.objects.filter(email=email).exists():
                    messages.error(request, "Email address already registered. Please use a different email.")
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')
                
                # Create User
                user = User.objects.create(
                    username=username,
                    email=email,
                    password=make_password(password),
                    first_name=form_data.get('first_name').strip(),
                    last_name=form_data.get('last_name').strip(),
                    is_active=True
                )
                
                # Create Borrower
                borrower = Borrower.objects.create(
                    user=user,
                    first_name=form_data.get('first_name').strip(),
                    middle_name=form_data.get('middle_name', '').strip() or None,
                    last_name=form_data.get('last_name').strip(),
                    date_of_birth=date_of_birth,
                    gender=form_data.get('gender'),
                    marital_status=form_data.get('marital_status'),
                    mobile_number=form_data.get('mobile_number').strip(),
                    current_street_address=form_data.get('current_street_address').strip(),
                    current_city=form_data.get('current_city').strip(),
                    current_state=form_data.get('current_state').strip(),
                    current_postal_code=form_data.get('current_postal_code').strip(),
                    permanent_street_address=permanent_street_address,
                    permanent_city=permanent_city,
                    permanent_state=permanent_state,
                    permanent_postal_code=permanent_postal_code,
                    employment_status=employment_status,
                    company_name=company_name or None,
                    job_title=job_title or None,
                    monthly_income=monthly_income,
                    income_source=form_data.get('income_source').strip(),
                    bank_name=form_data.get('bank_name').strip(),
                    account_number=form_data.get('account_number').strip(),
                    is_verified=bool(form_data.get('is_verified')),
                    is_active=bool(form_data.get('is_active')),
                    terms_accepted=True
                )
                
                messages.success(request, f"Borrower {borrower.full_name} has been successfully added to your portfolio.")
                return redirect('company-borrower-lists')
                
        except IntegrityError:
            messages.error(request, "Registration failed due to a database error. Please try again.")
        except ValidationError as e:
            messages.error(request, f"Validation error: {str(e)}")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
    
    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html')


#Company Financial Report function
@company_required
def financialReports(request):
    company = request.user.company_profile

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    report_type = request.GET.get('reportType', '')
    date_range = request.GET.get('dateRange', '')

    # Date filtering logic
    today = timezone.now().date()
    start_date = None
    if date_range == 'last-30':
        start_date = today - datetime.timedelta(days=30)
    elif date_range == 'last-90':
        start_date = today - datetime.timedelta(days=90)
    elif date_range == 'last-year':
        start_date = today - datetime.timedelta(days=365)

    loan_filter = Q(company=company)
    if start_date:
        loan_filter &= Q(created_at__gte=start_date)

    # Financial metrics
    revenue = LoanApplication.objects.filter(loan_filter, status='approved').aggregate(total=Sum('amount'))['total'] or 0
    profit = LoanApplication.objects.filter(loan_filter, status='approved').aggregate(
        total=Sum('amount')  # Replace with profit calculation if available
    )['total'] or 0
    expenses = 0  # Replace with real expense logic if available

    # Example: summary by month (replace with real logic if needed)
    monthly_summary = []
    for i in range(3):
        month = today - datetime.timedelta(days=30 * i)
        month_start = month.replace(day=1)
        month_end = (month_start + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
        month_loans = LoanApplication.objects.filter(
            company=company,
            status='approved',
            created_at__gte=month_start,
            created_at__lte=month_end
        )
        month_revenue = month_loans.aggregate(total=Sum('amount'))['total'] or 0
        monthly_summary.append({
            'month': month_start.strftime('%B %Y'),
            'revenue': month_revenue,
        })

    context = {
        'search': search,
        'report_type': report_type,
        'date_range': date_range,
        'revenue': revenue,
        'profit': profit,
        'expenses': expenses,
        'monthly_summary': monthly_summary,
    }

    return render(request, 'ReportSubmenus/financialReports.html', context)

#Company Portfolio Health function
@company_required
def portfolioHealth(request):
    company = request.user.company_profile

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    date_range = request.GET.get('dateRange', '')

    # Base queryset
    loans_qs = LoanApplication.objects.filter(company=company)
    total_loans = loans_qs.count()
    active_loans = loans_qs.filter(status='approved').count()
    delinquent_loans = loans_qs.filter(status='delinquent').count()
    defaulted_loans = loans_qs.filter(status='defaulted').count()
    portfolio_value = loans_qs.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0

    delinquency_rate = round((delinquent_loans / total_loans * 100), 2) if total_loans else 0
    default_rate = round((defaulted_loans / total_loans * 100), 2) if total_loans else 0

    # Example: summary by product type
    product_summary = []
    for key, label in dict(company.LOAN_PRODUCT_CHOICES).items():
        count = loans_qs.filter(product_type=key).count()
        delinquent = loans_qs.filter(product_type=key, status='delinquent').count()
        defaulted = loans_qs.filter(product_type=key, status='defaulted').count()
        product_summary.append({
            'label': label,
            'count': count,
            'delinquent': delinquent,
            'defaulted': defaulted,
        })

    context = {
        'search': search,
        'date_range': date_range,
        'active_loans': active_loans,
        'portfolio_value': portfolio_value,
        'delinquency_rate': delinquency_rate,
        'default_rate': default_rate,
        'product_summary': product_summary,
        'total_loans': total_loans,
    }

    return render(request, 'ReportSubmenus/portfolioHealth.html', context)

#Company Operational Reports function
@company_required
def operationalReports(request):
    company = request.user.company_profile

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    date_range = request.GET.get('dateRange', '')

    # Example metrics (replace with real queries as needed)
    team_members = company.team_members.count() if hasattr(company, 'team_members') else 5  # Example fallback
    avg_processing_time = LoanApplication.objects.filter(
        company=company, status='approved', approved_date__isnull=False
    ).annotate(
        proc_time=models.F('approved_date') - models.F('created_at')
    ).aggregate(avg=Avg('proc_time'))['avg']
    avg_processing_days = avg_processing_time.days if avg_processing_time else 0

    loans_processed = LoanApplication.objects.filter(company=company, status='approved').count()
    client_acquisition_cost = 500  # Replace with real calculation if available

    # Example: team performance summary (replace with real logic)
    team_performance = [
        {'name': 'Alice', 'loans_processed': 24, 'avg_processing_days': 3},
        {'name': 'Bob', 'loans_processed': 18, 'avg_processing_days': 4},
        {'name': 'Carol', 'loans_processed': 15, 'avg_processing_days': 2},
    ]

    context = {
        'search': search,
        'date_range': date_range,
        'team_members': team_members,
        'avg_processing_days': avg_processing_days,
        'loans_processed': loans_processed,
        'client_acquisition_cost': client_acquisition_cost,
        'team_performance': team_performance,
    }

    return render(request, 'ReportSubmenus/operationalReports.html', context)

@company_required
def view_loan_application(request, application_id):
    company = request.user.company_profile
    application = get_object_or_404(LoanApplication, id=application_id)

    # Ensure the company is authorized to view this application
    if application.company != company:
        return HttpResponseForbidden("You are not authorized to view this application.")

    context = {
        'application': application,
    }
    return render(request, 'CompanyPages/view_loan_application.html', context)

@company_required
def approve_loan_application(request, application_id):
    if request.method == 'POST':
        company = request.user.company_profile
        try:
            application = LoanApplication.objects.get(id=application_id, company=company)
            application.status = 'approved'
            application.approved_date = timezone.now()
            application.save()
            messages.success(request, f"Loan application #{application.id} has been approved.")
        except LoanApplication.DoesNotExist:
            messages.error(request, "Loan application not found or you don't have permission to approve it.")
    return redirect('company-loan-applications')

@company_required
def reject_loan_application(request, application_id):
    if request.method == 'POST':
        company = request.user.company_profile
        try:
            application = LoanApplication.objects.get(id=application_id, company=company)
            # You might want to add a 'rejected' status to your model choices
            application.status = 'rejected' 
            application.save()
            messages.warning(request, f"Loan application #{application.id} has been rejected.")
        except LoanApplication.DoesNotExist:
            messages.error(request, "Loan application not found or you don't have permission to reject it.")
    return redirect('company-loan-applications')