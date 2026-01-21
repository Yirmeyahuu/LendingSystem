from django.contrib import admin
from django.utils.html import format_html
from .models import Borrower


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'company_name', 'monthly_income_display', 
                    'employment_status', 'loan_status_badge', 'created_at']
    list_filter = ['employment_status', 'marital_status', 'gender', 'company', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'mobile_number', 'company__company_name']
    readonly_fields = ['created_at', 'updated_at', 'duplicate_check_hash', 'age', 
                       'full_name', 'current_address_full', 'permanent_address_full']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'middle_name', 'last_name', 'full_name', 'date_of_birth', 
                      'age', 'gender', 'marital_status')
        }),
        ('Contact Information', {
            'fields': ('email', 'mobile_number')
        }),
        ('Current Address', {
            'fields': ('current_street_address', 'current_city', 'current_state', 
                      'current_postal_code', 'current_address_full'),
            'classes': ('collapse',)
        }),
        ('Permanent Address', {
            'fields': ('permanent_street_address', 'permanent_city', 'permanent_state', 
                      'permanent_postal_code', 'permanent_address_full'),
            'classes': ('collapse',)
        }),
        ('Employment & Financial', {
            'fields': ('employment_status', 'company_name', 'job_title', 
                      'monthly_income', 'income_source')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_number'),
            'classes': ('collapse',)
        }),
        ('Consent & Company', {
            'fields': ('company', 'terms_accepted', 'marketing_consent')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at', 'duplicate_check_hash'),
            'classes': ('collapse',)
        }),
    )
    
    def company_name(self, obj):
        if obj.company:
            return format_html(
                '<a href="/admin/CompanyApp/company/{}/change/">{}</a>',
                obj.company.id,
                obj.company.company_name
            )
        return format_html('<span style="color: #6b7280;">No Company</span>')
    company_name.short_description = 'Applied Company'
    
    def monthly_income_display(self, obj):
        # Fix: Use {0} instead of direct f-string formatting
        return format_html(
            '<span style="color: #10b981; font-weight: bold;">₱{0}</span>',
            '{:,.2f}'.format(float(obj.monthly_income))
        )
    monthly_income_display.short_description = 'Monthly Income'
    
    def loan_status_badge(self, obj):
        if hasattr(obj, 'loan_application'):
            status = obj.loan_application.status
            colors = {
                'pending': '#fbbf24',
                'approved': '#10b981',
                'rejected': '#ef4444',
                'review': '#3b82f6',
                'delinquent': '#dc2626',
                'completed': '#059669',
            }
            color = colors.get(status, '#6b7280')
            return format_html(
                '<a href="/admin/CompanyApp/loanapplication/{}/change/" style="background-color: {}; color: white; padding: 4px 12px; border-radius: 9999px; font-weight: bold; text-decoration: none;">{}</a>',
                obj.loan_application.id,
                color,
                status.upper()
            )
        return format_html('<span style="color: #6b7280;">No Loan</span>')
    loan_status_badge.short_description = 'Loan Status'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('company', 'loan_application')
        return queryset