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
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.hashers import make_password
from decimal import Decimal, InvalidOperation
import re
from django.views.decorators.http import require_http_methods
from django.contrib.humanize.templatetags.humanize import intcomma, naturaltime
from collections import defaultdict



#Company Dashboard function
@company_required
def companyDashboard(request):
    company = request.user.company_profile
    
    # Basic Statistics - Remove is_active filters
    total_applications = LoanApplication.objects.filter(
        company=company
    ).count()
    
    active_loans = LoanApplication.objects.filter(
        company=company,
        status='approved'
    ).count()
    
    total_disbursed = LoanApplication.objects.filter(
        company=company,
        status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate default rate
    total_loans_count = LoanApplication.objects.filter(
        company=company,
        status__in=['approved', 'defaulted']
    ).count()
    
    defaulted_count = LoanApplication.objects.filter(
        company=company,
        status='defaulted'
    ).count()
    
    default_rate = round((defaulted_count / total_loans_count * 100), 2) if total_loans_count else 0

    # Fetch recent applications for this company (last 5)
    recent_applications = LoanApplication.objects.filter(
        company=company
    ).select_related('borrower').order_by('-created_at')[:5]

    # --- Chart Data for Loan Applications Overview ---
    today = timezone.now().date()
    
    # 7 Days Data
    seven_days_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = LoanApplication.objects.filter(
            company=company,
            created_at__date=day
        ).count()
        seven_days_data.append(count)
    
    # 30 Days Data
    thirty_days_data = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        count = LoanApplication.objects.filter(
            company=company,
            created_at__date=day
        ).count()
        thirty_days_data.append(count)
    
    # 90 Days Data
    ninety_days_data = []
    for i in range(89, -1, -1):
        day = today - timedelta(days=i)
        count = LoanApplication.objects.filter(
            company=company,
            created_at__date=day
        ).count()
        ninety_days_data.append(count)
    
    # Chart data
    chart_data = {
        '7': seven_days_data,
        '30': thirty_days_data,
        '90': ninety_days_data,
    }

    # --- Notifications and Alerts ---
    notifications = []
    
    # 1. New Applications (last 24 hours)
    new_apps = LoanApplication.objects.filter(
        company=company,
        status='pending',
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    if new_apps > 0:
        notifications.append({
            'type': 'new_application',
            'message': f'{new_apps} new loan application{"s" if new_apps > 1 else ""} pending review',
            'created_at': timezone.now(),
            'icon': 'fas fa-file-alt',
            'color': 'blue'
        })
    
    # 2. Recently Approved Applications (last 24 hours)
    recent_approved = LoanApplication.objects.filter(
        company=company,
        status='approved',
        approved_date__gte=timezone.now() - timedelta(hours=24)
    ).select_related('borrower')
    
    for app in recent_approved[:3]:  # Show last 3
        notifications.append({
            'type': 'approved',
            'message': f'Loan approved for {app.borrower.full_name}',
            'related_application': app,
            'created_at': app.approved_date,
            'icon': 'fas fa-check-circle',
            'color': 'green'
        })
    
    # 3. Overdue Loans
    overdue_loans = LoanApplication.objects.filter(
        company=company,
        status='approved'
    ).count()
    
    if overdue_loans > 0:
        notifications.append({
            'type': 'overdue',
            'message': f'{overdue_loans} loan{"s" if overdue_loans > 1 else ""} overdue',
            'created_at': timezone.now(),
            'icon': 'fas fa-exclamation-triangle',
            'color': 'red'
        })
    
    # 4. High Value Applications (over 500k)
    high_value_apps = LoanApplication.objects.filter(
        company=company,
        status='pending',
        amount__gte=500000,
        created_at__gte=timezone.now() - timedelta(hours=48)
    ).select_related('borrower')
    
    for app in high_value_apps[:2]:  # Show last 2
        notifications.append({
            'type': 'high_value',
            'message': f'High value loan request from {app.borrower.full_name}',
            'related_application': app,
            'created_at': app.created_at,
            'icon': 'fas fa-star',
            'color': 'yellow'
        })
    
    # 5. Applications Requiring Review
    review_required = LoanApplication.objects.filter(
        company=company,
        status='review'
    ).count()
    
    if review_required > 0:
        notifications.append({
            'type': 'review',
            'message': f'{review_required} application{"s" if review_required > 1 else ""} require{"s" if review_required == 1 else ""} additional review',
            'created_at': timezone.now(),
            'icon': 'fas fa-search',
            'color': 'orange'
        })
    
    # Sort notifications by created_at (most recent first)
    notifications.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Limit to 5 most recent notifications
    notifications = notifications[:5]

    # --- Monthly Performance Summary ---
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

    # Satisfaction Score (if you have a rating field)
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
        'chart_data': chart_data,
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

    # Search by name or email
    if search:
        applications_qs = applications_qs.filter(
            Q(borrower__first_name__icontains=search) |
            Q(borrower__last_name__icontains=search) |
            Q(borrower__email__icontains=search) |
            Q(amount__icontains=search)
        )

    # Filter by status
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

    # Statistics
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
    """Return loan application details as JSON"""
    try:
        company = request.user.company_profile
        application = get_object_or_404(
            LoanApplication.objects.select_related('borrower'),
            id=application_id,
            company=company
        )
        
        borrower = application.borrower
        
        data = {
            'success': True,
            'application': {
                'id': application.id,
                'status': application.status,
                'amount': str(application.amount) if application.amount else '0',
                'product_type': application.product_type or 'Personal Loan',
                'term': application.term if application.term else None,
                'interest_rate': str(application.interest_rate) if application.interest_rate else None,
                'monthly_payment': str(application.monthly_payment) if application.monthly_payment else None,
                'total_payment': str(application.total_payment) if application.total_payment else None,
                'total_interest': str(application.total_interest) if application.total_interest else None,
                'created_at': application.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'approved_date': application.approved_date.strftime('%B %d, %Y at %I:%M %p') if application.approved_date else None,
                'borrower': {
                    'full_name': borrower.full_name,
                    'email': borrower.email,
                    'mobile_number': borrower.mobile_number or 'Not provided',
                    'date_of_birth': borrower.date_of_birth.strftime('%B %d, %Y') if borrower.date_of_birth else 'Not provided',
                    'gender': borrower.gender or 'Not specified',
                    'marital_status': borrower.marital_status or 'Not specified',
                    'current_address': borrower.current_address_full,
                    'permanent_address': borrower.permanent_address_full,
                    'employment_status': borrower.employment_status or 'Not specified',
                    'company_name': borrower.company_name,
                    'job_title': borrower.job_title,
                    'monthly_income': str(borrower.monthly_income) if borrower.monthly_income else '0',
                    'income_source': borrower.income_source or 'Not specified',
                    'bank_name': borrower.bank_name,
                    'account_number': borrower.account_number,
                }
            }
        }
        
        return JsonResponse(data)
        
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
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    # Base queryset - Only borrowers with APPROVED loans
    borrowers = Borrower.objects.filter(
        company=company,
        loan_application__status='approved'
    ).distinct().select_related('loan_application').annotate(
        outstanding_amount=Sum(
            'loan_application__amount',
            filter=Q(loan_application__company=company, loan_application__status='approved')
        )
    )
    
    # Apply search filter
    if search:
        borrowers = borrowers.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    # Apply status filter (for future payment status)
    if status:
        if status == 'delinquent':
            borrowers = borrowers.filter(
                loan_application__status='delinquent',
                loan_application__company=company
            )
    
    # Statistics - Only count APPROVED loans
    total_borrowers = Borrower.objects.filter(
        company=company,
        loan_application__status='approved'
    ).distinct().count()
    
    active_borrowers = Borrower.objects.filter(
        company=company,
        loan_application__status='approved'
    ).distinct().count()
    
    delinquent_borrowers = Borrower.objects.filter(
        company=company,
        loan_application__status='delinquent'
    ).distinct().count()
    
    portfolio_value = LoanApplication.objects.filter(
        company=company,
        status='approved'
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Pagination
    paginator = Paginator(borrowers, 10)
    page_number = request.GET.get('page', 1)
    
    try:
        borrowers_page = paginator.page(page_number)
    except PageNotAnInteger:
        borrowers_page = paginator.page(1)
    except EmptyPage:
        borrowers_page = paginator.page(paginator.num_pages)
    
    context = {
        'borrowers': borrowers_page,
        'total_borrowers': total_borrowers,
        'active_borrowers': active_borrowers,
        'delinquent_borrowers': delinquent_borrowers,
        'portfolio_value': portfolio_value,
        'search': search,
        'status': status,
        'paginator': paginator,
        'current_page': borrowers_page.number,
        'total_pages': paginator.num_pages,
        'has_previous': borrowers_page.has_previous(),
        'has_next': borrowers_page.has_next(),
        'previous_page_number': borrowers_page.previous_page_number() if borrowers_page.has_previous() else None,
        'next_page_number': borrowers_page.next_page_number() if borrowers_page.has_next() else None,
        'start_index': borrowers_page.start_index(),
        'end_index': borrowers_page.end_index(),
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
            'overdue': 'delinquent',
            'grace': 'review',
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
            start_date = today - timedelta(days=30)
            loans_qs = loans_qs.filter(created_at__gte=start_date)
        elif date_range == 'last-90':
            start_date = today - timedelta(days=90)
            loans_qs = loans_qs.filter(created_at__gte=start_date)
        elif date_range == 'last-year':
            start_date = today - timedelta(days=365)
            loans_qs = loans_qs.filter(created_at__gte=start_date)

    # Statistics
    total_active_loans = loans_qs.count()
    portfolio_value = loans_qs.aggregate(total=models.Sum('amount'))['total'] or 0

    # Loan Performance
    on_time = loans_qs.filter(status='approved').count()
    late = loans_qs.filter(status='delinquent').count()
    missed = loans_qs.filter(status='defaulted').count() if 'defaulted' in dict(LoanApplication._meta.get_field('status').choices) else 0
    total_perf = on_time + late + missed
    on_time_pct = round((on_time / total_perf * 100), 1) if total_perf else 0
    late_pct = round((late / total_perf * 100), 1) if total_perf else 0
    missed_pct = round((missed / total_perf * 100), 1) if total_perf else 0

    # Loan Distribution by product_type - Only show company's selected loan products
    product_types_map = dict(Company.LOAN_PRODUCT_CHOICES)
    distribution = []
    
    # Get only the loan products this company offers
    company_loan_products = company.loan_products if company.loan_products else []
    
    for product_key in company_loan_products:
        product_label = product_types_map.get(product_key, product_key)
        count = loans_qs.filter(product_type=product_key).count()
        amount = loans_qs.filter(product_type=product_key).aggregate(total=models.Sum('amount'))['total'] or 0
        percent = round((count / total_active_loans * 100), 1) if total_active_loans else 0
        distribution.append({
            'key': product_key,
            'label': product_label,
            'count': count,
            'amount': amount,
            'percent': percent,
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
        'company_loan_products': company_loan_products,
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



#Company Settings function
@company_required
def settings(request):
    company = request.user.company_profile
    total_loans = LoanApplication.objects.filter(company=company).count()

    if request.method == 'POST':
        try:
            # Company Information
            company.company_name = request.POST.get('company_name', company.company_name).strip()
            company.business_email = request.POST.get('business_email', company.business_email).strip()
            company.company_phone = request.POST.get('company_phone', company.company_phone).strip()
            
            # Handle website (can be empty)
            website = request.POST.get('website', '').strip()
            company.website = website if website else None
            
            # Address fields
            company.street_address = request.POST.get('street_address', company.street_address).strip()
            company.city = request.POST.get('city', company.city).strip()
            company.state = request.POST.get('state', company.state).strip()
            company.postal_code = request.POST.get('postal_code', company.postal_code).strip()

            # Loan Settings - Handle decimal fields properly
            min_interest = request.POST.get('min_interest_rate', '').strip()
            if min_interest:
                try:
                    company.min_interest_rate = Decimal(min_interest)
                except (InvalidOperation, ValueError):
                    messages.error(request, 'Invalid minimum interest rate. Please enter a valid number.')
                    return redirect('company-settings')
            
            max_interest = request.POST.get('max_interest_rate', '').strip()
            if max_interest:
                try:
                    company.max_interest_rate = Decimal(max_interest)
                except (InvalidOperation, ValueError):
                    messages.error(request, 'Invalid maximum interest rate. Please enter a valid number.')
                    return redirect('company-settings')
            
            # Handle loan term fields (integers)
            min_term = request.POST.get('min_loan_term', '').strip()
            if min_term:
                try:
                    company.min_loan_term = int(min_term)
                except ValueError:
                    messages.error(request, 'Invalid minimum loan term. Please enter a valid number.')
                    return redirect('company-settings')
            
            max_term = request.POST.get('max_loan_term', '').strip()
            if max_term:
                try:
                    company.max_loan_term = int(max_term)
                except ValueError:
                    messages.error(request, 'Invalid maximum loan term. Please enter a valid number.')
                    return redirect('company-settings')
            
            # Handle late payment fee
            late_fee = request.POST.get('late_payment_fee', '').strip()
            if late_fee:
                try:
                    company.late_payment_fee = Decimal(late_fee)
                except (InvalidOperation, ValueError):
                    messages.error(request, 'Invalid late payment fee. Please enter a valid number.')
                    return redirect('company-settings')
            else:
                company.late_payment_fee = None
            
            # Validate interest rates
            if company.min_interest_rate and company.max_interest_rate:
                if company.min_interest_rate > company.max_interest_rate:
                    messages.error(request, 'Minimum interest rate cannot be greater than maximum interest rate.')
                    return redirect('company-settings')
            
            # Validate loan terms
            if company.min_loan_term and company.max_loan_term:
                if company.min_loan_term > company.max_loan_term:
                    messages.error(request, 'Minimum loan term cannot be greater than maximum loan term.')
                    return redirect('company-settings')
            
            company.save()
            messages.success(request, 'Your settings have been updated successfully.')
            
        except ValidationError as e:
            messages.error(request, f"Error saving settings: {e}")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
        
        return redirect('company-settings')

    context = {
        'company': company,
        'total_loans': total_loans,
    }
    return render(request, 'CompanyPages/companySettings.html', context)



#Company Active Borrowers Function
@company_required
def activeBorrowers(request):
    company = request.user.company_profile

    # Borrowers with APPROVED loans only
    active_borrowers_qs = Borrower.objects.filter(
        loan_application__company=company,
        loan_application__status='approved'
    ).distinct().select_related('loan_application')

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
def applicationHistory(request):
    """View all loan applications with their status"""
    company = request.user.company_profile
    
    # Get filter parameters
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset - All applications to this company
    applications = LoanApplication.objects.filter(
        company=company
    ).select_related('borrower').order_by('-created_at')
    
    # Apply search filter
    if search:
        applications = applications.filter(
            Q(borrower__first_name__icontains=search) |
            Q(borrower__last_name__icontains=search) |
            Q(borrower__email__icontains=search)
        )
    
    # Apply status filter
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Statistics
    total_applications = applications.count()
    pending_count = applications.filter(status='pending').count()
    approved_count = applications.filter(status='approved').count()
    rejected_count = applications.filter(status='rejected').count()
    completed_count = applications.filter(status='completed').count() if 'completed' in [choice[0] for choice in LoanApplication.STATUS_CHOICES] else 0
    
    # Calculate values
    total_approved_value = applications.filter(status='approved').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    total_rejected_value = applications.filter(status='rejected').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Pagination
    paginator = Paginator(applications, 20)
    page_number = request.GET.get('page', 1)
    
    try:
        applications_page = paginator.page(page_number)
    except PageNotAnInteger:
        applications_page = paginator.page(1)
    except EmptyPage:
        applications_page = paginator.page(paginator.num_pages)
    
    context = {
        'applications': applications_page,
        'total_applications': total_applications,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'completed_count': completed_count,
        'total_approved_value': total_approved_value,
        'total_rejected_value': total_rejected_value,
        'search': search,
        'status_filter': status_filter,
        'paginator': paginator,
        'current_page': applications_page.number,
        'total_pages': paginator.num_pages,
        'has_previous': applications_page.has_previous(),
        'has_next': applications_page.has_next(),
        'previous_page_number': applications_page.previous_page_number() if applications_page.has_previous() else None,
        'next_page_number': applications_page.next_page_number() if applications_page.has_next() else None,
        'start_index': applications_page.start_index(),
        'end_index': applications_page.end_index(),
    }
    
    return render(request, 'CompanyPages/companyApplicationHistory.html', context)


#Company Add Borrower function
@company_required
def addBorrowers(request):
    company = request.user.company_profile

    if request.method == 'POST':
        try:
            form_data = request.POST
            
            # Validate required fields (removed username, email, password fields)
            required_fields = [
                'first_name', 'last_name', 'date_of_birth', 'gender', 'marital_status',
                'mobile_number', 'email', 'current_street_address', 'current_city', 'current_state',
                'current_postal_code', 'employment_status', 'monthly_income', 'income_source',
                'bank_name', 'account_number', 'loan_product_type', 'loan_amount', 'loan_term', 'interest_rate'
            ]
            
            missing_fields = [field.replace('_', ' ').title() for field in required_fields 
                            if not form_data.get(field, '').strip()]
            
            if missing_fields:
                messages.error(request, f"Please fill in all required fields: {', '.join(missing_fields)}")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            
            # Extract and validate form data
            email = form_data.get('email').strip().lower()
            first_name = form_data.get('first_name').strip()
            last_name = form_data.get('last_name').strip()
            
            # Check for existing borrower with this company
            import hashlib
            check_string = f"{first_name}{last_name}{email}".lower()
            duplicate_hash = hashlib.sha256(check_string.encode()).hexdigest()
            
            existing_borrower = Borrower.objects.filter(
                company=company,
                duplicate_check_hash=duplicate_hash
            ).first()
            
            if existing_borrower:
                if hasattr(existing_borrower, 'loan_application'):
                    if existing_borrower.loan_application.status == 'approved':
                        messages.error(request, f'{first_name} {last_name} already has an active loan with your company.')
                        return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
                    elif existing_borrower.loan_application.status == 'pending':
                        messages.error(request, f'{first_name} {last_name} already has a pending application with your company.')
                        return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            
            # Validate email
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                messages.error(request, "Please enter a valid email address.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            
            # Validate monthly income
            try:
                monthly_income = Decimal(form_data.get('monthly_income'))
                if monthly_income < 0:
                    messages.error(request, "Monthly income cannot be negative.")
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            except (InvalidOperation, ValueError):
                messages.error(request, "Please enter a valid monthly income amount.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            
            # Validate date of birth
            try:
                date_of_birth = datetime.strptime(form_data.get('date_of_birth'), '%Y-%m-%d').date()
                today = datetime.now().date()
                age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
                
                if age < 18:
                    messages.error(request, "Borrower must be at least 18 years old.")
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
                
                if age > 100:
                    messages.error(request, "Please enter a valid date of birth.")
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
                    
            except ValueError:
                messages.error(request, "Please enter a valid date of birth.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            
            # Validate loan amount is within company limits
            try:
                loan_amount = Decimal(form_data.get('loan_amount'))
                if loan_amount < company.min_loan_amount or loan_amount > company.max_loan_amount:
                    messages.error(request, f'Loan amount must be between ₱{company.min_loan_amount:,.2f} and ₱{company.max_loan_amount:,.2f}')
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            except (InvalidOperation, ValueError):
                messages.error(request, "Please enter a valid loan amount.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            
            # Validate loan term
            try:
                loan_term = int(form_data.get('loan_term'))
                if loan_term < company.min_loan_term or loan_term > company.max_loan_term:
                    messages.error(request, f'Loan term must be between {company.min_loan_term} and {company.max_loan_term} months')
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            except ValueError:
                messages.error(request, "Please enter a valid loan term.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            
            # Validate interest rate
            try:
                interest_rate = Decimal(form_data.get('interest_rate'))
                if interest_rate < company.min_interest_rate or interest_rate > company.max_interest_rate:
                    messages.error(request, f'Interest rate must be between {company.min_interest_rate}% and {company.max_interest_rate}%')
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            except (InvalidOperation, ValueError):
                messages.error(request, "Please enter a valid interest rate.")
                return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            
            # Handle employment fields
            employment_status = form_data.get('employment_status')
            company_name = form_data.get('company_name', '').strip()
            job_title = form_data.get('job_title', '').strip()
            
            if employment_status in ['employed', 'self_employed']:
                if not company_name or not job_title:
                    messages.error(request, "Company name and job title are required for employed/self-employed status.")
                    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', {'company': company})
            
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
                # Create Borrower (no user account needed)
                borrower = Borrower.objects.create(
                    company=company,
                    first_name=first_name,
                    middle_name=form_data.get('middle_name', '').strip() or None,
                    last_name=last_name,
                    email=email,
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
                    terms_accepted=True,
                    marketing_consent=bool(form_data.get('marketing_consent'))
                )
                
                # Create LoanApplication with APPROVED status (company directly approves)
                loan_app = LoanApplication.objects.create(
                    borrower=borrower,
                    company=company,
                    product_type=form_data.get('loan_product_type'),
                    amount=loan_amount,
                    term=loan_term,
                    interest_rate=interest_rate,
                    status='approved',  # Automatically approved when company adds
                    approved_date=timezone.now()  # Set approval date
                )
                
                # Calculate loan payments and save
                loan_app.calculate_loan_payment()
                loan_app.save()
                
                messages.success(request, f"✓ Borrower {borrower.full_name} has been successfully added with an approved loan of ₱{loan_amount:,.2f}!")
                return redirect('company-borrower-lists')
                
        except IntegrityError:
            messages.error(request, "Failed to add borrower due to a database error. Please try again.")
        except ValidationError as e:
            messages.error(request, f"Validation error: {str(e)}")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
    
    context = {
        'company': company
    }
    return render(request, 'BorrowerSubmenus/companyAddBorrowers.html', context)




@company_required
def approve_loan_application(request, application_id):
    if request.method == 'POST':
        company = request.user.company_profile
        try:
            application = LoanApplication.objects.get(id=application_id, company=company)
            
            # Check if already approved
            if application.status == 'approved':
                messages.info(request, f"Loan application #{application.id} is already approved.")
            else:
                application.status = 'approved'
                application.approved_date = timezone.now()
                application.save()
                messages.success(request, f"✓ Loan application #{application.id} for {application.borrower.full_name} has been successfully approved!")
                
        except LoanApplication.DoesNotExist:
            messages.error(request, "Loan application not found or you don't have permission to approve it.")
    else:
        messages.error(request, "Invalid request method.")
        
    return redirect('company-loan-applications')


@company_required
def reject_loan_application(request, application_id):
    if request.method == 'POST':
        company = request.user.company_profile
        try:
            application = LoanApplication.objects.get(id=application_id, company=company)
            
            # Check if already rejected
            if application.status == 'rejected':
                messages.info(request, f"Loan application #{application.id} is already rejected.")
            else:
                application.status = 'rejected'
                application.save()
                messages.warning(request, f"✗ Loan application #{application.id} for {application.borrower.full_name} has been rejected.")
                
        except LoanApplication.DoesNotExist:
            messages.error(request, "Loan application not found or you don't have permission to reject it.")
    else:
        messages.error(request, "Invalid request method.")
        
    return redirect('company-loan-applications')




# View Borrower Details from Active Loan (AJAX)
@company_required
def viewBorrowerDetailsFromLoan(request, loan_id):
    """Return borrower details from a loan application as JSON"""
    try:
        company = request.user.company_profile
        loan = get_object_or_404(
            LoanApplication.objects.select_related('borrower'),
            id=loan_id,
            company=company,
            status='approved'
        )
        
        borrower = loan.borrower
        
        # Format addresses safely
        current_address = None
        if borrower.current_street_address:
            current_address = f"{borrower.current_street_address}, {borrower.current_city}, {borrower.current_state} {borrower.current_postal_code}"
        
        permanent_address = None
        if borrower.permanent_street_address:
            permanent_address = f"{borrower.permanent_street_address}, {borrower.permanent_city}, {borrower.permanent_state} {borrower.permanent_postal_code}"
        
        data = {
            'success': True,
            'loan': {
                'id': loan.id,
                'product_type': loan.product_type,
                'amount': str(loan.amount),
                'term': loan.term if loan.term else None,
                'interest_rate': str(loan.interest_rate) if loan.interest_rate else None,
                'monthly_payment': str(loan.monthly_payment) if loan.monthly_payment else None,
                'total_payment': str(loan.total_payment) if loan.total_payment else None,
                'total_interest': str(loan.total_interest) if loan.total_interest else None,
                'status': loan.status,
                'approved_date': loan.approved_date.strftime('%B %d, %Y at %I:%M %p') if loan.approved_date else None,
                'created_at': loan.created_at.strftime('%B %d, %Y at %I:%M %p'),
            },
            'borrower': {
                'id': borrower.id,
                'full_name': borrower.full_name,
                'email': borrower.email,  # Direct from borrower model
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
        
        return JsonResponse(data)
        
    except LoanApplication.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Loan not found or not active.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)




# View Borrower Details (AJAX)
@company_required
def viewBorrowerDetails(request, borrower_id):
    """Return borrower details with their loans as JSON"""
    try:
        company = request.user.company_profile
        
        # Get borrower who has loans with this company
        borrower = get_object_or_404(
            Borrower,
            id=borrower_id,
            loan_application__company=company
        )
        
        # Get all loans for this borrower (not just approved)
        loans = LoanApplication.objects.filter(
            borrower=borrower,
            company=company
        ).order_by('-created_at')
        
        # Product type mapping
        product_type_map = dict(Company.LOAN_PRODUCT_CHOICES)
        
        # Format loans data with payment calculations
        loans_data = []
        for loan in loans:
            loans_data.append({
                'id': loan.id,
                'product_type': loan.product_type,
                'product_type_display': product_type_map.get(loan.product_type, loan.product_type),
                'amount': str(loan.amount),
                'term': loan.term if loan.term else None,
                'interest_rate': str(loan.interest_rate) if loan.interest_rate else None,
                'monthly_payment': str(loan.monthly_payment) if loan.monthly_payment else None,
                'total_payment': str(loan.total_payment) if loan.total_payment else None,
                'total_interest': str(loan.total_interest) if loan.total_interest else None,
                'status': loan.status,
                'approved_date': loan.approved_date.strftime('%B %d, %Y') if loan.approved_date else None,
                'created_at': loan.created_at.strftime('%B %d, %Y'),
            })
        
        data = {
            'success': True,
            'borrower': {
                'id': borrower.id,
                'full_name': borrower.full_name,
                'first_name': borrower.first_name,
                'last_name': borrower.last_name,
                'email': borrower.email,
                'mobile_number': borrower.mobile_number or None,
                'date_of_birth': borrower.date_of_birth.strftime('%B %d, %Y') if borrower.date_of_birth else None,
                'gender': borrower.gender or None,
                'marital_status': borrower.marital_status or None,
                'employment_status': borrower.employment_status or None,
                'company_name': borrower.company_name or None,
                'job_title': borrower.job_title or None,
                'monthly_income': str(borrower.monthly_income) if borrower.monthly_income else None,
            },
            'loans': loans_data
        }
        
        return JsonResponse(data)
        
    except Borrower.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Borrower not found.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)