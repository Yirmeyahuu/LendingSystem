from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from BorrowerApp.models import Borrower

class Company(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('checking', 'Checking Account'),
        ('savings', 'Savings Account'),
        ('business', 'Business Account'),
    ]
    
    LOAN_PRODUCT_CHOICES = [
        ('personal_loans', 'Personal Loans'),
        ('business_loans', 'Business Loans'),
        ('salary_loans', 'Salary Loans'),
        ('auto_loans', 'Auto Loans'),
        ('home_loans', 'Home Loans'),
        ('payday_loans', 'Payday Loans'),
    ]
    
    # Link to Django User model for authentication
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_profile')
    
    # Step 1: Company Information
    company_name = models.CharField(max_length=255, verbose_name="Company Legal Name")
    registration_number = models.CharField(max_length=100, verbose_name="Business Registration Number")
    tax_id = models.CharField(max_length=50, verbose_name="Tax ID/EIN Number")
    street_address = models.CharField(max_length=255, verbose_name="Street Address")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, verbose_name="State/Province")
    postal_code = models.CharField(max_length=20)
    contact_person = models.CharField(max_length=255, verbose_name="Primary Contact Person")
    contact_title = models.CharField(max_length=100, verbose_name="Contact Person Title")
    company_phone = models.CharField(max_length=20, verbose_name="Company Phone Number")
    business_email = models.EmailField(verbose_name="Business Email Address")
    website = models.URLField(blank=True, null=True, verbose_name="Company Website")
    
    # Step 2: Loan Products & Operations
    loan_products = models.JSONField(verbose_name="Types of Loans Offered", help_text="Stored as list of selected loan types")
    min_loan_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Minimum Loan Amount")
    max_loan_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Maximum Loan Amount")
    min_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="Minimum Interest Rate (%)")
    max_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="Maximum Interest Rate (%)")
    processing_fee = models.DecimalField(max_digits=4, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(10)], blank=True, null=True, verbose_name="Processing Fee (%)")
    late_payment_fee = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True, verbose_name="Late Payment Fee")
    min_loan_term = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(600)], verbose_name="Minimum Loan Term (months)")
    max_loan_term = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(600)], verbose_name="Maximum Loan Term (months)")
    lending_policies = models.TextField(verbose_name="Loan Approval Criteria & Policies")
    
    # Step 3: Banking Information
    bank_name = models.CharField(max_length=255)
    account_holder_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=20)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    swift_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="SWIFT Code")
    monthly_volume = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Expected Monthly Loan Volume")
    years_in_business = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="Years in Lending Business")
    
    # Step 4: Account Settings & Compliance
    terms_accepted = models.BooleanField(default=False, verbose_name="Terms Accepted")
    compliance_accepted = models.BooleanField(default=False, verbose_name="Compliance Acknowledged")
    marketing_consent = models.BooleanField(default=False, verbose_name="Marketing Consent")
    
    # System fields
    is_approved = models.BooleanField(default=False, verbose_name="Registration Approved")
    date_registered = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['-date_registered']
    
    def __str__(self):
        return self.company_name
    
    def clean(self):
        """Custom validation for model fields"""
        # Validate loan amount ranges
        if self.min_loan_amount and self.max_loan_amount:
            if self.max_loan_amount <= self.min_loan_amount:
                raise ValidationError("Maximum loan amount must be greater than minimum loan amount")
        
        # Validate interest rate ranges
        if self.min_interest_rate and self.max_interest_rate:
            if self.max_interest_rate <= self.min_interest_rate:
                raise ValidationError("Maximum interest rate must be greater than minimum interest rate")
        
        # Validate loan term ranges
        if self.min_loan_term and self.max_loan_term:
            if self.max_loan_term <= self.min_loan_term:
                raise ValidationError("Maximum loan term must be greater than minimum loan term")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def loan_products_display(self):
        """Return formatted display of loan products"""
        if not self.loan_products:
            return "No loan products selected"
        
        product_map = dict(self.LOAN_PRODUCT_CHOICES)
        return ", ".join([product_map.get(product, product) for product in self.loan_products])
    
    @property
    def full_address(self):
        """Return formatted full address"""
        return f"{self.street_address}, {self.city}, {self.state} {self.postal_code}"
    


class LoanApplication(models.Model):
    borrower = models.ForeignKey(Borrower, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    product_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_date = models.DateTimeField(null=True, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('review', 'Under Review')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    type = models.CharField(max_length=50)  # e.g., 'overdue', 'new_application', 'payment_received'
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_application = models.ForeignKey('LoanApplication', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type.title()} - {self.message[:30]}"