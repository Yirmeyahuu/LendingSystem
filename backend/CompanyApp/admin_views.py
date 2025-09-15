from django.shortcuts import get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import Company

@staff_member_required
def approve_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    # Approve the company
    company.is_approved = True
    company.save()
    
    # Activate the user account
    company.user.is_active = True
    company.user.save()
    
    # Send approval email
    send_approval_email(company)
    
    messages.success(request, f'Company "{company.company_name}" has been approved.')
    return redirect('admin:CompanyApp_company_changelist')

@staff_member_required
def reject_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    # Reject the company
    company.is_approved = False
    company.save()
    
    # Deactivate the user account
    company.user.is_active = False
    company.user.save()
    
    # Send rejection email
    send_rejection_email(company)
    
    messages.warning(request, f'Company "{company.company_name}" has been rejected.')
    return redirect('admin:CompanyApp_company_changelist')

def send_approval_email(company):
    """Send approval notification email"""
    subject = 'Company Registration Approved - Avendro'
    message = f"""
    Dear {company.contact_person},
    
    Congratulations! Your company registration for {company.company_name} has been approved.
    
    You can now log in to your account and start using our lending platform.
    
    Login URL: {settings.SITE_URL}/login/
    Username: {company.user.username}
    
    Best regards,
    Avendro Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [company.business_email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Failed to send approval email: {e}")

def send_rejection_email(company):
    """Send rejection notification email"""
    subject = 'Company Registration Update - Avendro'
    message = f"""
    Dear {company.contact_person},
    
    Thank you for your interest in becoming a lending partner with Avendro.
    
    After reviewing your application for {company.company_name}, we are unable to approve your registration at this time.
    
    If you have questions about this decision, please contact our support team.
    
    Best regards,
    Avendro Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [company.business_email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Failed to send rejection email: {e}")