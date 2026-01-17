"""
Dashboard Client API Validation Schemas
Provides comprehensive validation for all dashboard endpoints
"""
import re
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, date


class DashboardSchemas:
    """Validation schemas for dashboard client endpoints"""
    
    @staticmethod
    def validate_profile_update(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate user profile update data
        
        Args:
            data: Dictionary containing profile update data
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # First name validation
        first_name = data.get('firstName', '').strip()
        if first_name:
            if len(first_name) < 2:
                errors['firstName'] = 'First name must be at least 2 characters'
            elif len(first_name) > 50:
                errors['firstName'] = 'First name must not exceed 50 characters'
            else:
                cleaned_data['first_name'] = first_name
        
        # Last name validation
        last_name = data.get('lastName', '').strip()
        if last_name:
            if len(last_name) < 2:
                errors['lastName'] = 'Last name must be at least 2 characters'
            elif len(last_name) > 50:
                errors['lastName'] = 'Last name must not exceed 50 characters'
            else:
                cleaned_data['last_name'] = last_name
        
        # Phone validation
        phone = data.get('phone', '').strip()
        if phone:
            if not DashboardSchemas._validate_phone(phone):
                errors['phone'] = 'Invalid phone number format'
            else:
                cleaned_data['phone'] = phone
        
        # Date of birth validation
        dob = data.get('dateOfBirth')
        if dob:
            try:
                if isinstance(dob, str):
                    dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
                else:
                    dob_date = dob
                
                # Check if date is in the past and user is at least 18
                today = date.today()
                age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                
                if dob_date >= today:
                    errors['dateOfBirth'] = 'Date of birth must be in the past'
                elif age < 18:
                    errors['dateOfBirth'] = 'You must be at least 18 years old'
                else:
                    cleaned_data['date_of_birth'] = dob_date
            except (ValueError, TypeError):
                errors['dateOfBirth'] = 'Invalid date format. Use YYYY-MM-DD'
        
        # Passport number validation
        passport_number = data.get('passportNumber', '').strip()
        if passport_number:
            if len(passport_number) < 6 or len(passport_number) > 20:
                errors['passportNumber'] = 'Passport number must be between 6 and 20 characters'
            else:
                cleaned_data['passport_number'] = passport_number
        
        # Passport expiry validation
        passport_expiry = data.get('passportExpiry')
        if passport_expiry:
            try:
                if isinstance(passport_expiry, str):
                    expiry_date = datetime.strptime(passport_expiry, '%Y-%m-%d').date()
                else:
                    expiry_date = passport_expiry
                
                # Check if expiry is in the future
                if expiry_date <= date.today():
                    errors['passportExpiry'] = 'Passport expiry date must be in the future'
                else:
                    cleaned_data['passport_expiry'] = expiry_date
            except (ValueError, TypeError):
                errors['passportExpiry'] = 'Invalid date format. Use YYYY-MM-DD'
        
        # Nationality validation
        nationality = data.get('nationality', '').strip()
        if nationality:
            if len(nationality) < 2 or len(nationality) > 50:
                errors['nationality'] = 'Nationality must be between 2 and 50 characters'
            else:
                cleaned_data['nationality'] = nationality
        
        # Preferred airline validation
        preferred_airline = data.get('preferredAirline', '').strip()
        if preferred_airline:
            if len(preferred_airline) > 100:
                errors['preferredAirline'] = 'Preferred airline must not exceed 100 characters'
            else:
                cleaned_data['preferred_airline'] = preferred_airline
        
        # Frequent flyer numbers validation
        frequent_flyer = data.get('frequentFlyerNumbers')
        if frequent_flyer:
            if isinstance(frequent_flyer, dict):
                cleaned_data['frequent_flyer_numbers'] = frequent_flyer
            else:
                errors['frequentFlyerNumbers'] = 'Frequent flyer numbers must be a dictionary'
        
        # Dietary preferences validation
        dietary_prefs = data.get('dietaryPreferences', '').strip()
        if dietary_prefs:
            if len(dietary_prefs) > 200:
                errors['dietaryPreferences'] = 'Dietary preferences must not exceed 200 characters'
            else:
                cleaned_data['dietary_preferences'] = dietary_prefs
        
        # Special assistance validation
        special_assistance = data.get('specialAssistance', '').strip()
        if special_assistance:
            if len(special_assistance) > 1000:
                errors['specialAssistance'] = 'Special assistance must not exceed 1000 characters'
            else:
                cleaned_data['special_assistance'] = special_assistance
        
        # Company name validation (for corporate users)
        company_name = data.get('companyName', '').strip()
        if company_name:
            if len(company_name) > 200:
                errors['companyName'] = 'Company name must not exceed 200 characters'
            else:
                cleaned_data['company_name'] = company_name
        
        # Company tax ID validation
        company_tax_id = data.get('companyTaxId', '').strip()
        if company_tax_id:
            if len(company_tax_id) > 50:
                errors['companyTaxId'] = 'Company tax ID must not exceed 50 characters'
            else:
                cleaned_data['company_tax_id'] = company_tax_id
        
        # Billing address validation
        billing_address = data.get('billingAddress', '').strip()
        if billing_address:
            if len(billing_address) > 500:
                errors['billingAddress'] = 'Billing address must not exceed 500 characters'
            else:
                cleaned_data['billing_address'] = billing_address
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    @staticmethod
    def validate_subscription_upgrade(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate subscription upgrade request
        
        Args:
            data: Dictionary containing subscription upgrade data
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Subscription tier validation
        tier = data.get('tier', '').strip().lower()
        valid_tiers = ['bronze', 'silver', 'gold']
        
        if not tier:
            errors['tier'] = 'Subscription tier is required'
        elif tier not in valid_tiers:
            errors['tier'] = f'Invalid subscription tier. Must be one of: {", ".join(valid_tiers)}'
        else:
            cleaned_data['tier'] = tier
        
        # Payment method ID validation (for Stripe)
        payment_method_id = data.get('paymentMethodId', '').strip()
        if payment_method_id:
            cleaned_data['payment_method_id'] = payment_method_id
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    @staticmethod
    def validate_booking_filters(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate booking filter parameters
        
        Args:
            data: Dictionary containing filter parameters
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Status filter validation
        status = data.get('status', '').strip().lower()
        valid_statuses = ['pending', 'confirmed', 'cancelled', 'completed', 'refunded', 'requested', 'all']
        
        if status:
            if status not in valid_statuses:
                errors['status'] = f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            else:
                cleaned_data['status'] = status if status != 'all' else None
        
        # Booking type filter validation
        booking_type = data.get('type', '').strip().lower()
        valid_types = ['flight', 'package', 'hotel', 'custom', 'all']
        
        if booking_type:
            if booking_type not in valid_types:
                errors['type'] = f'Invalid booking type. Must be one of: {", ".join(valid_types)}'
            else:
                cleaned_data['booking_type'] = booking_type if booking_type != 'all' else None
        
        # Date range validation
        start_date = data.get('startDate')
        if start_date:
            try:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                cleaned_data['start_date'] = start_date
            except (ValueError, TypeError):
                errors['startDate'] = 'Invalid date format. Use YYYY-MM-DD'
        
        end_date = data.get('endDate')
        if end_date:
            try:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                cleaned_data['end_date'] = end_date
            except (ValueError, TypeError):
                errors['endDate'] = 'Invalid date format. Use YYYY-MM-DD'
        
        # Validate date range logic
        if 'start_date' in cleaned_data and 'end_date' in cleaned_data:
            if cleaned_data['start_date'] > cleaned_data['end_date']:
                errors['dateRange'] = 'Start date must be before end date'
        
        # Pagination validation
        page = data.get('page', 1)
        try:
            page = int(page)
            if page < 1:
                errors['page'] = 'Page must be greater than 0'
            else:
                cleaned_data['page'] = page
        except (ValueError, TypeError):
            errors['page'] = 'Page must be a valid integer'
        
        per_page = data.get('perPage', 10)
        try:
            per_page = int(per_page)
            if per_page < 1 or per_page > 100:
                errors['perPage'] = 'Per page must be between 1 and 100'
            else:
                cleaned_data['per_page'] = per_page
        except (ValueError, TypeError):
            errors['perPage'] = 'Per page must be a valid integer'
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    @staticmethod
    def validate_contact_form(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate contact form submission
        
        Args:
            data: Dictionary containing contact form data
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Category validation
        category = data.get('category', '').strip().lower()
        valid_categories = ['general', 'booking', 'payment', 'technical', 'feedback']
        
        if not category:
            errors['category'] = 'Category is required'
        elif category not in valid_categories:
            errors['category'] = f'Invalid category. Must be one of: {", ".join(valid_categories)}'
        else:
            cleaned_data['category'] = category
        
        # Subject validation
        subject = data.get('subject', '').strip()
        if not subject:
            errors['subject'] = 'Subject is required'
        elif len(subject) < 5:
            errors['subject'] = 'Subject must be at least 5 characters'
        elif len(subject) > 200:
            errors['subject'] = 'Subject must not exceed 200 characters'
        else:
            cleaned_data['subject'] = subject
        
        # Message validation
        message = data.get('message', '').strip()
        if not message:
            errors['message'] = 'Message is required'
        elif len(message) < 20:
            errors['message'] = 'Message must be at least 20 characters'
        elif len(message) > 2000:
            errors['message'] = 'Message must not exceed 2000 characters'
        else:
            cleaned_data['message'] = message
        
        # Optional booking reference
        booking_ref = data.get('bookingReference', '').strip()
        if booking_ref:
            cleaned_data['booking_reference'] = booking_ref
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    @staticmethod
    def validate_booking_cancellation(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate booking cancellation request
        
        Args:
            data: Dictionary containing cancellation data
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Cancellation reason validation
        reason = data.get('reason', '').strip()
        if reason:
            if len(reason) > 500:
                errors['reason'] = 'Reason must not exceed 500 characters'
            else:
                cleaned_data['reason'] = reason
        
        # Request refund flag
        request_refund = data.get('requestRefund', True)
        cleaned_data['request_refund'] = bool(request_refund)
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    # Helper validation methods
    
    @staticmethod
    def _validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        # Remove common formatting characters
        cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
        # Check if it's 10-15 digits
        return cleaned.isdigit() and 10 <= len(cleaned) <= 15
    
    @staticmethod
    def validate_settings_update(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate settings update data
        """
        errors = {}
        cleaned_data = {}
        
        # Boolean fields
        bool_fields = [
            'emailNotifications', 
            'marketingEmails', 
            'smsNotifications', 
            'profileVisibility', 
            'dataSharing'
        ]
        
        for field in bool_fields:
            if field in data:
                if not isinstance(data[field], bool):
                   errors[field] = f'{field} must be a boolean'
                else:
                   cleaned_data[field] = data[field]
                   
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
