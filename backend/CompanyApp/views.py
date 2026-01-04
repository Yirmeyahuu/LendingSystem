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
from django.views.decorators.http import require_http_methods
from django.contrib.humanize.templatetags.humanize import intcomma, naturaltime
from collections import defaultdict



#Company Dashboard function
@company_required
def companyDashboard(request):
    company = request.user.company_profile
    
    # Basic Statistics - Exclude archived borrowers
    total_applications = LoanApplication.objects.filter(
        company=company,
        borrower__is_active=True
    ).count()
    
    active_loans = LoanApplication.objects.filter(
        company=company,
        status='approved',
        borrower__is_active=True
    ).count()
    
    total_disbursed = LoanApplication.objects.filter(
        company=company,
        status='approved',
        borrower__is_active=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate default rate
    total_loans_count = LoanApplication.objects.filter(
        company=company,
        status__in=['approved', 'defaulted'],
        borrower__is_active=True
    ).count()
    
    defaulted_count = LoanApplication.objects.filter(
        company=company,
        status='defaulted',
        borrower__is_active=True
    ).count()
    
    default_rate = round((defaulted_count / total_loans_count * 100), 2) if total_loans_count else 0

    # Fetch recent applications for this company (last 5)
    recent_applications = LoanApplication.objects.filter(
        company=company,
        borrower__is_active=True
    ).select_related('borrower', 'borrower__user').order_by('-created_at')[:5]

    # --- Chart Data for Loan Applications Overview ---
    today = timezone.now().date()
    
    # 7 Days Data
    seven_days_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = LoanApplication.objects.filter(
            company=company,
            borrower__is_active=True,
            created_at__date=day
        ).count()
        seven_days_data.append(count)
    
    # 30 Days Data
    thirty_days_data = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        count = LoanApplication.objects.filter(
            company=company,
            borrower__is_active=True,
            created_at__date=day
        ).count()
        thirty_days_data.append(count)
    
    # 90 Days Data
    ninety_days_data = []
    for i in range(89, -1, -1):
        day = today - timedelta(days=i)
        count = LoanApplication.objects.filter(
            company=company,
            borrower__is_active=True,
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
        borrower__is_active=True,
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
        borrower__is_active=True,
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
    
    # 3. Overdue Loans (if you have a due_date field)
    # Assuming loans have payment schedules
    overdue_loans = LoanApplication.objects.filter(
        company=company,
        status='approved',
        borrower__is_active=True,
        # Add your overdue condition here
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
        borrower__is_active=True,
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
        status='review',
        borrower__is_active=True
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
        borrower__is_active=True,
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
                'term': application.term if application.term else None,
                'interest_rate': str(application.interest_rate) if application.interest_rate else None,
                'monthly_payment': str(application.monthly_payment) if application.monthly_payment else None,
                'total_payment': str(application.total_payment) if application.total_payment else None,
                'total_interest': str(application.total_interest) if application.total_interest else None,
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
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    risk = request.GET.get('risk', '')
    
    # Base queryset - only active borrowers
    borrowers = Borrower.objects.filter(
        loanapplication__company=company,
        is_active=True  # Only show active borrowers
    ).distinct().annotate(
        outstanding_amount=Sum(
            'loanapplication__amount',
            filter=Q(loanapplication__company=company, loanapplication__status='approved')
        )
    )
    
    # Apply search filter
    if search:
        borrowers = borrowers.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    # Apply status filter
    if status:
        if status == 'active':
            borrowers = borrowers.filter(is_active=True)
        elif status == 'inactive':
            borrowers = borrowers.filter(is_active=False)
        elif status == 'delinquent':
            borrowers = borrowers.filter(
                loanapplication__status='delinquent',
                loanapplication__company=company
            )
    
    # Statistics - only for active borrowers
    total_borrowers = Borrower.objects.filter(
        loanapplication__company=company,
        is_active=True
    ).distinct().count()
    
    active_borrowers = Borrower.objects.filter(
        loanapplication__company=company,
        loanapplication__status='approved',
        is_active=True
    ).distinct().count()
    
    delinquent_borrowers = Borrower.objects.filter(
        loanapplication__company=company,
        loanapplication__status='delinquent',
        is_active=True
    ).distinct().count()
    
    portfolio_value = LoanApplication.objects.filter(
        company=company,
        status='approved',
        borrower__is_active=True  # Only active borrowers
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
        'risk': risk,
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



# View Borrower Details from Active Loan (AJAX)
@company_required
def viewBorrowerDetailsFromLoan(request, loan_id):
    """
    Return borrower details from a loan application as JSON for modal display
    """
    try:
        company = request.user.company_profile
        loan = get_object_or_404(
            LoanApplication.objects.select_related('borrower__user'),
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




# Archive Borrower (AJAX)
@company_required
@require_http_methods(["POST"])
def archiveBorrower(request, borrower_id):
    """
    Archive a borrower (set is_active to False)
    """
    try:
        company = request.user.company_profile
        
        # Get borrower who has loans with this company
        borrower = get_object_or_404(
            Borrower.objects.select_related('user'),
            id=borrower_id,
            loanapplication__company=company
        )
        
        # Check if borrower has any active/pending loans
        active_loans = LoanApplication.objects.filter(
            borrower=borrower,
            company=company,
            status__in=['approved', 'pending']
        ).count()
        
        if active_loans > 0:
            return JsonResponse({
                'success': False,
                'message': 'Cannot archive borrower with active or pending loans.'
            }, status=400)
        
        # Archive the borrower
        borrower.is_active = False
        borrower.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Borrower archived successfully.'
        })
        
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


# Restore Borrower (AJAX)
@company_required
@require_http_methods(["POST"])
def restoreBorrower(request, borrower_id):
    """
    Restore an archived borrower (set is_active to True)
    """
    try:
        company = request.user.company_profile
        
        # Get archived borrower who has loans with this company
        borrower = get_object_or_404(
            Borrower.objects.select_related('user'),
            id=borrower_id,
            loanapplication__company=company,
            is_active=False  # Only restore archived borrowers
        )
        
        # Restore the borrower
        borrower.is_active = True
        borrower.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Borrower restored successfully.'
        })
        
    except Borrower.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Archived borrower not found.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)

