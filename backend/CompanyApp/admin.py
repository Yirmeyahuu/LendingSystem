from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Company, LoanApplication, Payment, Notification


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'city', 'state', 'is_approved', 'date_registered']
    list_filter = ['is_approved', 'city', 'state', 'date_registered']
    search_fields = ['company_name', 'registration_number', 'business_email', 'city']
    readonly_fields = ['date_registered', 'date_updated']
    
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'registration_number', 'tax_id', 'user')
        }),
        ('Contact Details', {
            'fields': ('street_address', 'city', 'state', 'postal_code', 
                      'contact_person', 'contact_title', 'company_phone', 'business_email', 'website')
        }),
        ('Loan Products & Terms', {
            'fields': ('loan_products', 'min_loan_amount', 'max_loan_amount', 
                      'min_interest_rate', 'max_interest_rate', 'min_loan_term', 'max_loan_term',
                      'processing_fee', 'late_payment_fee', 'lending_policies')
        }),
        ('Compliance', {
            'fields': ('terms_accepted', 'compliance_accepted', 'marketing_consent')
        }),
        ('System Information', {
            'fields': ('is_approved', 'date_registered', 'date_updated'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'borrower_name', 'company_name', 'amount', 'term', 'interest_rate', 'status', 'created_at']
    list_filter = ['status', 'company', 'created_at', 'approved_date']
    search_fields = ['borrower__first_name', 'borrower__last_name', 'borrower__email', 'company__company_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Application Info', {
            'fields': ('borrower', 'company', 'status', 'rating', 'approved_date')
        }),
        ('Loan Details', {
            'fields': ('product_type', 'amount', 'term', 'interest_rate')
        }),
        ('Calculated Amounts', {
            'fields': ('monthly_payment', 'total_payment', 'total_interest'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def borrower_name(self, obj):
        return obj.borrower.full_name
    borrower_name.short_description = 'Borrower'
    
    def company_name(self, obj):
        return obj.company.company_name if obj.company else 'N/A'
    company_name.short_description = 'Company'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'loan_application', 'amount', 'due_date', 'paid_date', 'status', 'method']
    list_filter = ['status', 'method', 'due_date', 'paid_date']
    search_fields = ['loan_application__borrower__first_name', 'loan_application__borrower__last_name', 
                     'reference_number']
    readonly_fields = ['created_at']
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('loan_application', 'amount', 'method', 'status')
        }),
        ('Dates', {
            'fields': ('due_date', 'paid_date')
        }),
        ('Receipt Details', {
            'fields': ('reference_number', 'receipt'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'company', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at', 'company']
    search_fields = ['message', 'company__company_name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('company', 'type', 'message', 'related_application', 'is_read')
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )