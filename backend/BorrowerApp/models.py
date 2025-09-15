from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from decimal import Decimal

class Borrower(models.Model):
    # Personal Information
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    
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
    
    # Sign In Credentials (linked to Django User model)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='borrower_profile')
    
    # Consent and Agreement fields
    terms_accepted = models.BooleanField(default=False)
    marketing_consent = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'borrower'
        ordering = ['-created_at']
        verbose_name = 'Borrower'
        verbose_name_plural = 'Borrowers'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user.email})"
    
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
        return self.current_address_full  # Use current address if permanent is not provided
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def save(self, *args, **kwargs):
        """Override save method to handle permanent address logic"""
        # If permanent address fields are empty, copy from current address
        if not self.permanent_street_address:
            self.permanent_street_address = self.current_street_address
            self.permanent_city = self.current_city
            self.permanent_state = self.current_state
            self.permanent_postal_code = self.current_postal_code
        
        super().save(*args, **kwargs)
    
    def get_employment_display_with_details(self):
        """Returns employment status with company details if applicable"""
        employment = self.get_employment_status_display()
        if self.employment_status in ['employed', 'self_employed'] and self.company_name:
            return f"{employment} at {self.company_name}"
        return employment
    
    def is_eligible_for_loan(self):
        """Basic eligibility check - can be expanded with business logic"""
        # Must be at least 18 years old
        if self.age < 18:
            return False
        
        # Must have some income
        if self.monthly_income <= 0:
            return False
        
        # Must have verified identity
        if not self.is_verified:
            return False
        
        # Must have active status
        if not self.is_active:
            return False
        
        return True
    