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