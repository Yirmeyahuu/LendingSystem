from django.db import models
from django.core.validators import RegexValidator, MinValueValidator
from decimal import Decimal

class Borrower(models.Model):
    """
    Borrower model - Each application to a company creates a new borrower record
    This allows tracking of application history across multiple companies
    """
    # Link to Company
    company = models.ForeignKey('CompanyApp.Company', on_delete=models.CASCADE, related_name='borrowers', null=True, blank=True)
    
    # Personal Information
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    
    # Email for communication
    email = models.EmailField(verbose_name="Email Address", null=True, blank=True)
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('separated', 'Separated'),
    ]   
    marital_status = models.CharField(max_length=15, choices=MARITAL_STATUS_CHOICES)
    
    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    mobile_number = models.CharField(validators=[phone_regex], max_length=17)
    
    # Current Address
    current_street_address = models.CharField(max_length=255)
    current_city = models.CharField(max_length=100)
    current_state = models.CharField(max_length=100)
    current_postal_code = models.CharField(max_length=20)
    
    # Permanent Address
    permanent_street_address = models.CharField(max_length=255, blank=True, null=True)
    permanent_city = models.CharField(max_length=100, blank=True, null=True)
    permanent_state = models.CharField(max_length=100, blank=True, null=True)
    permanent_postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Employment and Financial Information
    EMPLOYMENT_STATUS_CHOICES = [
        ('employed', 'Employed'),
        ('self_employed', 'Self-Employed'),
        ('unemployed', 'Unemployed'),
        ('student', 'Student'),
        ('retired', 'Retired'),
    ]
    employment_status = models.CharField(max_length=15, choices=EMPLOYMENT_STATUS_CHOICES)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    monthly_income = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    income_source = models.TextField()
    
    # Bank Account Details
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    
    # Consent
    terms_accepted = models.BooleanField(default=False)
    marketing_consent = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Duplicate detection fields
    duplicate_check_hash = models.CharField(max_length=64, db_index=True, blank=True)
    
    class Meta:
        db_table = 'borrower'
        ordering = ['-created_at']
        verbose_name = 'Borrower Application'
        verbose_name_plural = 'Borrower Applications'
        # One borrower can have multiple applications to different companies
        unique_together = [['email', 'company']]
        indexes = [
            models.Index(fields=['email', 'company', 'date_of_birth']),
            models.Index(fields=['first_name', 'last_name', 'email']),
        ]
    
    def __str__(self):
        company_name = self.company.company_name if self.company else "No Company"
        loan_status = self.loan_application.status if hasattr(self, 'loan_application') else 'No Loan'
        return f"{self.first_name} {self.last_name} - {company_name} ({loan_status})"
    
    @property
    def full_name(self):
        """Returns the full name of the borrower"""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    @property
    def current_address_full(self):
        """Returns the complete current address"""
        return f"{self.current_street_address}, {self.current_city}, {self.current_state} {self.current_postal_code}"
    
    @property
    def permanent_address_full(self):
        """Returns the complete permanent address"""
        if self.permanent_street_address:
            return f"{self.permanent_street_address}, {self.permanent_city}, {self.permanent_state} {self.permanent_postal_code}"
        return self.current_address_full
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    @property
    def application_status(self):
        """Get the application status from related loan application"""
        if hasattr(self, 'loan_application'):
            return self.loan_application.status
        return 'pending'
    
    def save(self, *args, **kwargs):
        """Override save to handle permanent address and duplicate detection"""
        # Copy current to permanent if empty
        if not self.permanent_street_address:
            self.permanent_street_address = self.current_street_address
            self.permanent_city = self.current_city
            self.permanent_state = self.current_state
            self.permanent_postal_code = self.current_postal_code
        
        # Generate duplicate check hash
        import hashlib
        check_string = f"{self.first_name}{self.last_name}{self.email}".lower()
        self.duplicate_check_hash = hashlib.sha256(check_string.encode()).hexdigest()
        
        super().save(*args, **kwargs)