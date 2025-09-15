from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'company_name', 
        'contact_person', 
        'business_email', 
        'registration_status',
        'date_registered',
        'monthly_volume',
        'years_in_business',
        'approval_actions'
    ]
    
    list_filter = [
        'is_approved',
        'date_registered', 
        'account_type',
        'years_in_business'
    ]
    
    search_fields = [
        'company_name',
        'registration_number', 
        'tax_id',
        'business_email',
        'contact_person'
    ]
    
    readonly_fields = [
        'user',
        'date_registered', 
        'date_updated',
        'loan_products_display',
        'full_address'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'user',
                'company_name',
                'registration_number',
                'tax_id',
                'contact_person',
                'contact_title',
                'business_email',
                'company_phone',
                'website'
            )
        }),
        ('Address', {
            'fields': (
                'street_address',
                'city',
                'state',
                'postal_code',
                'full_address'
            )
        }),
        ('Loan Products & Terms', {
            'fields': (
                'loan_products_display',
                'min_loan_amount',
                'max_loan_amount',
                'min_interest_rate',
                'max_interest_rate',
                'processing_fee',
                'late_payment_fee',
                'min_loan_term',
                'max_loan_term',
                'lending_policies'
            )
        }),
        ('Banking Information', {
            'fields': (
                'bank_name',
                'account_holder_name',
                'account_number',
                'routing_number',
                'account_type',
                'swift_code',
                'monthly_volume',
                'years_in_business'
            )
        }),
        ('Compliance & Settings', {
            'fields': (
                'terms_accepted',
                'compliance_accepted',
                'marketing_consent',
                'is_approved'
            )
        }),
        ('System Information', {
            'fields': (
                'date_registered',
                'date_updated'
            )
        })
    )
    
    actions = ['approve_companies', 'reject_companies']
    
    def registration_status(self, obj):
        if obj.is_approved:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Approved</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Pending</span>'
            )
    registration_status.short_description = 'Status'
    
    def approval_actions(self, obj):
        if not obj.is_approved:
            return format_html(
                '<button onclick="approveCompany({})" style="background: green; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">Approve</button>&nbsp;'
                '<button onclick="rejectCompany({})" style="background: red; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">Reject</button>',
                obj.pk, obj.pk
            )
        else:
            return format_html('<span style="color: green;">✓ Approved</span>')
    approval_actions.short_description = 'Actions'
    approval_actions.allow_tags = True
    
    def approve_companies(self, request, queryset):
        updated = 0
        for company in queryset:
            if not company.is_approved:
                company.is_approved = True
                company.save()
                # Activate the user account
                company.user.is_active = True
                company.user.save()
                updated += 1
        
        self.message_user(request, f'{updated} companies have been approved.')
    approve_companies.short_description = "Approve selected companies"
    
    def reject_companies(self, request, queryset):
        updated = 0
        for company in queryset:
            if company.is_approved:
                company.is_approved = False
                company.save()
                # Deactivate the user account
                company.user.is_active = False
                company.user.save()
                updated += 1
        
        self.message_user(request, f'{updated} companies have been rejected.')
    reject_companies.short_description = "Reject selected companies"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')