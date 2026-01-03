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
from CompanyApp.models import LoanApplication, Company
from django.utils import timezone

#borrower dashboard function
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

#borrower logout function
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

#borrower Active Loans function
@borrower_required
def activeLoans(request):
    borrower = request.user.borrower_profile
    active_loans = LoanApplication.objects.filter(borrower=borrower, status='approved').order_by('-created_at')

    context = {
        'active_loans': active_loans,
    }
    return render(request, 'MyLoanSubmenus/activeLoans.html', context)

#borrower Loan History function
@borrower_required
def loanHistory(request):
    borrower = request.user.borrower_profile
    loan_history = LoanApplication.objects.filter(borrower=borrower).order_by('-created_at')

    context = {
        'loan_history': loan_history,
    }
    return render(request, 'MyLoanSubmenus/loanHistory.html', context)


#borrower Apply Loan function
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
        term = request.POST.get('term')
        interest_rate = request.POST.get('interest_rate')

        # Basic validation
        errors = []
        if not company_id:
            errors.append("Please select a lender.")
        if not product_type:
            errors.append("Please select a loan product.")
        if not amount:
            errors.append("Please enter a loan amount.")
        if not term:
            errors.append("Please select a loan term.")

        try:
            amount = Decimal(amount)
            if amount <= 0:
                errors.append("Loan amount must be greater than zero.")
        except Exception:
            errors.append("Invalid loan amount.")

        try:
            term = int(term)
            if term <= 0:
                errors.append("Loan term must be greater than zero.")
        except Exception:
            errors.append("Invalid loan term.")

        try:
            interest_rate = Decimal(interest_rate)
            if interest_rate < 0:
                errors.append("Interest rate cannot be negative.")
        except Exception:
            errors.append("Invalid interest rate.")

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

        # Create LoanApplication with calculations
        loan = LoanApplication.objects.create(
            borrower=borrower,
            company=company,
            product_type=product_type,
            amount=amount,
            term=term,
            interest_rate=interest_rate,
            status='pending'
        )
        
        # Calculate loan payment details
        loan.calculate_loan_payment()
        loan.save()

        messages.success(request, f"Your loan application has been submitted! Monthly payment: ₱{loan.monthly_payment:,.2f}")
        return redirect('borrower-apply-loan')

    return render(request, 'ApplyLoan/applyLoan.html', {'companies': companies})


# AJAX endpoint to get company loan details
@borrower_required
def get_company_loan_details(request, company_id):
    """Return company loan details as JSON for calculator"""
    try:
        company = Company.objects.get(id=company_id, is_approved=True)
        
        data = {
            'success': True,
            'company': {
                'id': company.id,
                'name': company.company_name,
                'min_loan_amount': str(company.min_loan_amount),
                'max_loan_amount': str(company.max_loan_amount),
                'min_interest_rate': str(company.min_interest_rate),
                'max_interest_rate': str(company.max_interest_rate),
                'min_loan_term': company.min_loan_term,
                'max_loan_term': company.max_loan_term,
                'processing_fee': str(company.processing_fee) if company.processing_fee else '0',
            }
        }
        
        return JsonResponse(data)
        
    except Company.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Company not found.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


# AJAX endpoint to calculate loan payment
@borrower_required
def calculate_loan_payment(request):
    """Calculate loan payment based on amount, interest rate, and term"""
    try:
        amount = Decimal(request.GET.get('amount', 0))
        interest_rate = Decimal(request.GET.get('interest_rate', 0))
        term = int(request.GET.get('term', 0))
        
        if amount <= 0 or term <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Invalid amount or term'
            }, status=400)
        
        # Calculate monthly payment
        monthly_rate = (interest_rate / 100) / 12
        
        if monthly_rate > 0:
            numerator = monthly_rate * (1 + monthly_rate) ** term
            denominator = (1 + monthly_rate) ** term - 1
            monthly_payment = amount * (numerator / denominator)
        else:
            monthly_payment = amount / term
        
        total_payment = monthly_payment * term
        total_interest = total_payment - amount
        
        data = {
            'success': True,
            'calculation': {
                'monthly_payment': str(round(monthly_payment, 2)),
                'total_payment': str(round(total_payment, 2)),
                'total_interest': str(round(total_interest, 2)),
                'principal': str(amount),
                'interest_rate': str(interest_rate),
                'term': term
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Calculation error: {str(e)}'
        }, status=500)




#borrower Payments function
@borrower_required
def borrowerPayments(request):
    borrower = request.user.borrower_profile
    from CompanyApp.models import LoanApplication, Payment

    if request.method == 'POST':
        loan_id = request.POST.get('loan_id')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        reference_number = request.POST.get('reference_number', '').strip()

        # Validate inputs
        errors = []
        if not loan_id:
            errors.append("Please select a loan.")
        if not amount:
            errors.append("Please enter payment amount.")
        if not payment_method:
            errors.append("Please select a payment method.")
        if not reference_number:
            errors.append("Please enter a payment reference number.")

        try:
            amount = Decimal(amount)
            if amount <= 0:
                errors.append("Payment amount must be greater than zero.")
        except Exception:
            errors.append("Invalid payment amount.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                # Get the approved loan
                loan = LoanApplication.objects.get(
                    id=loan_id,
                    borrower=borrower,
                    status='approved'
                )

                # Create payment record
                payment = Payment.objects.create(
                    loan_application=loan,
                    amount=amount,
                    method=payment_method,
                    reference_number=reference_number,
                    due_date=timezone.now(),
                    paid_date=timezone.now().date(),
                    status='paid'
                )

                messages.success(request, f"Payment of ₱{amount} has been recorded successfully! Reference: {reference_number}")
                return redirect('borrower-payments')

            except LoanApplication.DoesNotExist:
                messages.error(request, "Loan application not found or not approved.")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")

    # Get approved loans for the select dropdown
    approved_loans = LoanApplication.objects.filter(
        borrower=borrower,
        status='approved'
    ).order_by('-created_at')

    # Get all payments made by borrower
    payments = Payment.objects.filter(
        loan_application__borrower=borrower
    ).order_by('-due_date')

    context = {
        'approved_loans': approved_loans,
        'payments': payments,
    }
    return render(request, 'Payments/borrowerPayment.html', context)



#borrower Profile function
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

#borrower Update Security function
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

#borrower Change Password function
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