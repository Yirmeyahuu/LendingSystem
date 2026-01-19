from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from .models import Borrower
from CompanyApp.models import Company, LoanApplication
from decimal import Decimal
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import hashlib

def selectCompany(request):
    """Show list of approved companies - Filter out companies where borrower has active loan"""
    email = request.session.get('borrower_email', '')
    full_name = request.session.get('borrower_name', '')
    
    # Get all approved companies
    companies = Company.objects.filter(is_approved=True)
    
    # If we have borrower info in session, filter out companies with active loans
    if email and full_name:
        # Check which companies this borrower has active loans with
        active_loan_companies = Borrower.objects.filter(
            email__iexact=email,
            first_name__iexact=full_name.split()[0],
            last_name__iexact=full_name.split()[-1],
            loan_application__status='approved'
        ).values_list('company_id', flat=True)
        
        # Exclude companies with active loans
        companies = companies.exclude(id__in=active_loan_companies)
    
    context = {
        'companies': companies,
        'borrower_email': email,
        'has_active_session': bool(email and full_name)
    }
    return render(request, 'BorrowerApp/company_selection.html', context)


@require_http_methods(["POST"])
def check_existing_borrower(request, company_id):
    """Check if borrower already has an application with this company"""
    try:
        company = get_object_or_404(Company, id=company_id, is_approved=True)
        
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        if not email or not first_name or not last_name:
            return JsonResponse({
                'exists': False,
                'can_proceed': True
            })
        
        # Check for existing borrower
        check_string = f"{first_name}{last_name}{email}".lower()
        duplicate_hash = hashlib.sha256(check_string.encode()).hexdigest()
        
        existing_borrower = Borrower.objects.filter(
            company=company,
            duplicate_check_hash=duplicate_hash
        ).first()
        
        if existing_borrower and hasattr(existing_borrower, 'loan_application'):
            loan_app = existing_borrower.loan_application
            
            if loan_app.status == 'approved':
                return JsonResponse({
                    'exists': True,
                    'can_proceed': False,
                    'status': 'approved',
                    'message': f'You already have an active loan with {company.company_name}. Please contact the company to discuss your existing loan before applying for a new one.'
                })
            elif loan_app.status == 'pending':
                return JsonResponse({
                    'exists': True,
                    'can_proceed': False,
                    'status': 'pending',
                    'message': f'You already have a pending application with {company.company_name}. Please wait for review before submitting a new application.'
                })
            elif loan_app.status == 'rejected':
                return JsonResponse({
                    'exists': True,
                    'can_proceed': True,
                    'status': 'rejected',
                    'message': f'Your previous application was rejected. You may submit a new application.'
                })
        
        return JsonResponse({
            'exists': False,
            'can_proceed': True
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'can_proceed': True
        }, status=500)


def borrowerApplication(request, company_id):
    """Handle borrower loan application"""
    company = get_object_or_404(Company, id=company_id, is_approved=True)
    
    if request.method == 'POST':
        try:
            # Extract form data
            email = request.POST.get('email', '').strip().lower()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            
            # Check for existing application with this company
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
                        messages.error(request, 'You already have an active loan with this company.')
                        return redirect('select-company')
                    elif existing_borrower.loan_application.status == 'pending':
                        messages.warning(request, 'You already have a pending application with this company. Please wait for review.')
                        return redirect('select-company')
            
            # Validate loan amount is within company limits
            loan_amount = Decimal(request.POST.get('loan_amount'))
            if loan_amount < company.min_loan_amount or loan_amount > company.max_loan_amount:
                messages.error(request, f'Loan amount must be between ₱{company.min_loan_amount:,.2f} and ₱{company.max_loan_amount:,.2f}')
                return render(request, 'BorrowerPages/borrowerApplication.html', {'company': company})
            
            # Validate loan term
            loan_term = int(request.POST.get('loan_term'))
            if loan_term < company.min_loan_term or loan_term > company.max_loan_term:
                messages.error(request, f'Loan term must be between {company.min_loan_term} and {company.max_loan_term} months')
                return render(request, 'BorrowerPages/borrowerApplication.html', {'company': company})
            
            # Get interest rate from form
            interest_rate = Decimal(request.POST.get('interest_rate', company.min_interest_rate))
            
            with transaction.atomic():
                # Create Borrower
                borrower = Borrower.objects.create(
                    company=company,
                    first_name=first_name,
                    middle_name=request.POST.get('middle_name', '').strip() or None,
                    last_name=last_name,
                    email=email,
                    date_of_birth=datetime.strptime(request.POST.get('date_of_birth'), '%Y-%m-%d').date(),
                    gender=request.POST.get('gender'),
                    marital_status=request.POST.get('marital_status'),
                    mobile_number=request.POST.get('mobile_number'),
                    current_street_address=request.POST.get('current_street_address'),
                    current_city=request.POST.get('current_city'),
                    current_state=request.POST.get('current_state'),
                    current_postal_code=request.POST.get('current_postal_code'),
                    permanent_street_address=request.POST.get('permanent_street_address') or None,
                    permanent_city=request.POST.get('permanent_city') or None,
                    permanent_state=request.POST.get('permanent_state') or None,
                    permanent_postal_code=request.POST.get('permanent_postal_code') or None,
                    employment_status=request.POST.get('employment_status'),
                    company_name=request.POST.get('company_name') or None,
                    job_title=request.POST.get('job_title') or None,
                    monthly_income=Decimal(request.POST.get('monthly_income')),
                    income_source=request.POST.get('income_source'),
                    bank_name=request.POST.get('bank_name'),
                    account_number=request.POST.get('account_number'),
                    terms_accepted=True,
                    marketing_consent=bool(request.POST.get('marketing_consent'))
                )
                
                # Create LoanApplication with loan details
                loan_app = LoanApplication.objects.create(
                    borrower=borrower,
                    company=company,
                    product_type=request.POST.get('loan_product_type'),
                    amount=loan_amount,
                    term=loan_term,
                    interest_rate=interest_rate,
                    status='pending'
                )
                
                # Calculate loan payments and save
                loan_app.calculate_loan_payment()
                loan_app.save()
                
                # Store in session for future applications
                request.session['borrower_email'] = email
                request.session['borrower_name'] = f"{first_name} {last_name}"
                
                messages.success(request, 'Your loan application has been submitted successfully!')
                return redirect('application-success')
                
        except Exception as e:
            messages.error(request, f'Error submitting application: {str(e)}')
            return render(request, 'BorrowerApp/borrowerApplication.html', {'company': company})
    
    context = {
        'company': company
    }
    return render(request, 'BorrowerApp/borrowerApplication.html', context)


def applicationSuccess(request):
    """Show success page after application submission"""
    return render(request, 'BorrowerApp/application_success.html')