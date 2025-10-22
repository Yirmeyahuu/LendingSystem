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
from django.db.models import Count, Avg, Q, Sum
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

@company_required
def borrowerLists(request):
    company = request.user.company_profile

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')
    risk = request.GET.get('risk', '')

    # Base queryset

    borrowers_qs = Borrower.objects.all()

    # Annotate outstanding amount
    borrowers_qs = borrowers_qs.annotate(
        outstanding_amount=Sum('loanapplication__amount')
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

    context = {
        'total_borrowers': borrowers_qs.count(),
        'active_borrowers': borrowers_qs.filter(is_active=True).count(),
        'delinquent_borrowers': borrowers_qs.filter(
            loanapplication__company=company,
            loanapplication__status='delinquent'
        ).distinct().count(),
        'portfolio_value': LoanApplication.objects.filter(company=company, status='approved').aggregate(total=Sum('amount'))['total'] or 0,
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

@company_required
def potentialBorrowers(request):
    company = request.user.company_profile

    # Borrowers who have registered but have not applied for a loan
    potential_borrowers_qs = Borrower.objects.filter(
        loanapplication__isnull=True
    )

    total_potential_borrowers = potential_borrowers_qs.count()

    context = {
        'potential_borrowers': potential_borrowers_qs,
        'total_potential_borrowers': total_potential_borrowers,
    }
    return render(request, 'BorrowerSubmenus/companyPotentialBorrowers.html', context)

@company_required
def archivedBorrowers(request):
    company = request.user.company_profile

    # Borrowers who have fully repaid loans or whose accounts are closed
    archived_borrowers_qs = Borrower.objects.filter(
        Q(is_active=False) |
        Q(loanapplication__company=company, loanapplication__status='closed')
    ).distinct()

    total_archived_borrowers = archived_borrowers_qs.count()

    context = {
        'archived_borrowers': archived_borrowers_qs,
        'total_archived_borrowers': total_archived_borrowers,
    }
    return render(request, 'BorrowerSubmenus/companyArchivedBorrowers.html', context)


@company_required
def addBorrowers(request):
    company = request.user.company_profile

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        mobile_number = request.POST.get('mobile_number', '').strip()

        # Basic validation
        if first_name and last_name and email:
            # Create user and borrower (simplified, adjust for your user model)
            user = User.objects.create(username=email, email=email)
            borrower = Borrower.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                mobile_number=mobile_number,
                is_active=True
            )
            messages.success(request, "Borrower added successfully.")
            return redirect('company-add-borrowers')
        else:
            messages.error(request, "Please fill in all required fields.")

    # Show recently added borrowers (last 10)
    recent_borrowers = Borrower.objects.order_by('-created_at')[:10]

    context = {
        'recent_borrowers': recent_borrowers,
    }
    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', context)


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