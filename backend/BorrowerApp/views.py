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
from django.views.decorators.csrf import csrf_exempt
import traceback
from django.db.models import Count

def selectCompany(request):
    """Show list of approved companies - Filter out companies where borrower has active loan"""
    email = request.session.get('borrower_email', '')
    full_name = request.session.get('borrower_name', '')
    
    # Get all approved companies with borrower count and order by borrower count (descending)
    companies = Company.objects.filter(is_approved=True).annotate(
        borrower_count=Count('borrowers', distinct=True)  # Changed from 'borrower' to 'borrowers'
    ).order_by('-borrower_count', 'company_name')  # Order by count DESC, then name ASC
    
    # If we have borrower info in session, filter out companies with active loans
    if email and full_name:
        # Check which companies this borrower has active loans with
        active_loan_companies = Borrower.objects.filter(
            email__iexact=email,
            first_name__iexact=full_name.split()[0],
            last_name__iexact=full_name.split()[-1],
            loan_application__status='approved'
        ).values_list('company_id', flat=True)
        
        # Exclude companies with active loans but keep the annotation
        companies = companies.exclude(id__in=active_loan_companies)
    
    context = {
        'companies': companies,
        'borrower_email': email,
        'has_active_session': bool(email and full_name)
    }
    return render(request, 'BorrowerApp/company_selection.html', context)


@require_http_methods(["POST"])
def check_existing_borrower(request, company_id):
    """Check if borrower already has an application with ANY company"""
    try:
        from CompanyApp.models import Company
        from .models import Borrower
        
        company = get_object_or_404(Company, id=company_id, is_approved=True)
        
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        print(f"\n{'='*80}")
        print(f"CHECK EXISTING BORROWER - GLOBAL CHECK")
        print(f"{'='*80}")
        print(f"Applying to Company: {company.company_name} (ID: {company_id})")
        print(f"Email: {email}")
        print(f"Name: {first_name} {last_name}")
        
        if not email or not first_name or not last_name:
            print("Missing required fields - allowing application")
            return JsonResponse({
                'exists': False,
                'can_proceed': True
            })
        
        # ===== STEP 1: Check for existing borrower with ANY company =====
        all_borrowers_with_email = Borrower.objects.filter(
            email__iexact=email,
            first_name__iexact=first_name,
            last_name__iexact=last_name
        ).select_related('loan_application', 'company')
        
        print(f"\nFound {all_borrowers_with_email.count()} total borrower record(s) with this email across ALL companies:")
        
        # Track all applications
        active_loans = []
        pending_applications = []
        rejected_applications = []
        paid_loans = []
        
        for borrower in all_borrowers_with_email:
            company_name = borrower.company.company_name if borrower.company else "No Company"
            print(f"\n  Borrower ID: {borrower.id}")
            print(f"  Company: {company_name}")
            
            if hasattr(borrower, 'loan_application'):
                loan_app = borrower.loan_application
                print(f"  Loan Status: {loan_app.status}")
                print(f"  Loan Amount: {loan_app.amount}")
                print(f"  Total Payment: {loan_app.total_payment}")
                
                if loan_app.status == 'approved':
                    remaining_balance = loan_app.remaining_balance
                    print(f"  Remaining Balance: {remaining_balance}")
                    
                    if remaining_balance > 0:
                        active_loans.append({
                            'borrower': borrower,
                            'loan': loan_app,
                            'company': borrower.company,
                            'balance': remaining_balance
                        })
                    else:
                        paid_loans.append({
                            'borrower': borrower,
                            'loan': loan_app,
                            'company': borrower.company
                        })
                        
                elif loan_app.status == 'pending':
                    # Only track pending with THIS company
                    if borrower.company.id == company_id:
                        pending_applications.append({
                            'borrower': borrower,
                            'loan': loan_app,
                            'company': borrower.company
                        })
                        
                elif loan_app.status == 'rejected':
                    # Only track rejected with THIS company
                    if borrower.company.id == company_id:
                        rejected_applications.append({
                            'borrower': borrower,
                            'loan': loan_app,
                            'company': borrower.company
                        })
        
        # ===== STEP 2: Check for active loans (highest priority) =====
        if active_loans:
            print(f"\n❌ BLOCKING - Found {len(active_loans)} active loan(s) with outstanding balance:")
            
            # Get the loan with the highest balance or most recent
            primary_loan = active_loans[0]
            
            for loan_info in active_loans:
                print(f"  - Company: {loan_info['company'].company_name}")
                print(f"    Balance: ₱{loan_info['balance']:,.2f}")
            
            # Create message listing all companies with outstanding loans
            if len(active_loans) == 1:
                message = f"You currently have a pending balance of ₱{primary_loan['balance']:,.2f} with {primary_loan['company'].company_name}. Please settle your account before applying for a new loan. Thank you."
            else:
                companies_list = ", ".join([loan['company'].company_name for loan in active_loans])
                total_balance = sum(loan['balance'] for loan in active_loans)
                message = f"You currently have outstanding loans with multiple companies ({companies_list}) totaling ₱{total_balance:,.2f}. Please settle your accounts before applying for new loans. Thank you."
            
            return JsonResponse({
                'exists': True,
                'can_proceed': False,
                'status': 'approved',
                'has_balance': True,
                'remaining_balance': float(primary_loan['balance']),
                'total_loan': float(primary_loan['loan'].total_payment or 0),
                'total_paid': float(primary_loan['loan'].total_paid),
                'company_name': primary_loan['company'].company_name,
                'multiple_loans': len(active_loans) > 1,
                'loan_count': len(active_loans),
                'message': message
            })
        
        # ===== STEP 3: Check for pending applications with THIS company =====
        if pending_applications:
            print(f"\n⏳ BLOCKING - Pending application with THIS company")
            pending_app = pending_applications[0]
            return JsonResponse({
                'exists': True,
                'can_proceed': False,
                'status': 'pending',
                'message': f'You already have a pending application with {pending_app["company"].company_name}. Please wait for review before submitting a new application.'
            })
        
        # ===== STEP 4: Check for rejected applications with THIS company =====
        if rejected_applications:
            print(f"\nℹ️ ALLOWING - Previous application with THIS company was rejected")
            rejected_app = rejected_applications[0]
            return JsonResponse({
                'exists': True,
                'can_proceed': True,
                'status': 'rejected',
                'message': f'Your previous application with {rejected_app["company"].company_name} was rejected. You may submit a new application.'
            })
        
        # ===== STEP 5: Check for fully paid loans =====
        if paid_loans:
            print(f"\n✓ ALLOWING - Found {len(paid_loans)} fully paid loan(s)")
            for paid_loan in paid_loans:
                print(f"  - Company: {paid_loan['company'].company_name} (Fully Paid)")
            
            return JsonResponse({
                'exists': True,
                'can_proceed': True,
                'status': 'paid',
                'message': f'You have successfully completed previous loans. You may apply for a new loan.'
            })
        
        # ===== STEP 6: No existing applications found =====
        print(f"\n✓ NO EXISTING APPLICATIONS - Allowing new application")
        print(f"{'='*80}\n")
        return JsonResponse({
            'exists': False,
            'can_proceed': True
        })
        
    except Exception as e:
        print(f"\n❌ ERROR in check_existing_borrower:")
        print(f"  {str(e)}")
        import traceback
        print(traceback.format_exc())
        print(f"{'='*80}\n")
        
        return JsonResponse({
            'error': str(e),
            'can_proceed': True,
            'exists': False
        }, status=200)


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


