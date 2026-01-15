"""
Authentication validation schemas
Provides comprehensive validation for all authentication endpoints
"""
import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime


class AuthSchemas:
    """Validation schemas for authentication endpoints"""
    
    @staticmethod
    def validate_registration(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate user registration data
        
        Args:
            data: Dictionary containing registration data
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Full name validation and splitting
        full_name = data.get('fullName', '').strip()
        if not full_name:
            errors['fullName'] = 'Full name is required'
        elif len(full_name) < 2:
            errors['fullName'] = 'Full name must be at least 2 characters'
        else:
            # Split full name into first and last name
            name_parts = full_name.split(None, 1)  # Split on first whitespace
            cleaned_data['first_name'] = name_parts[0]
            cleaned_data['last_name'] = name_parts[1] if len(name_parts) > 1 else name_parts[0]
        
        # Email validation
        email = data.get('email', '').strip().lower()
        if not email:
            errors['email'] = 'Email is required'
        elif not AuthSchemas._validate_email_format(email):
            errors['email'] = 'Invalid email format'
        else:
            cleaned_data['email'] = email
        
        # Password validation
        password = data.get('password', '')
        confirm_password = data.get('confirmPassword', '')
        
        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        elif not AuthSchemas._validate_password_strength(password):
            errors['password'] = 'Password must contain at least one letter and one number'
        else:
            cleaned_data['password'] = password
        
        # Password confirmation
        if not confirm_password:
            errors['confirmPassword'] = 'Password confirmation is required'
        elif password != confirm_password:
            errors['confirmPassword'] = 'Passwords do not match'
        
        # Optional phone validation
        phone = data.get('phone', '').strip()
        if phone:
            if not AuthSchemas._validate_phone(phone):
                errors['phone'] = 'Invalid phone number format'
            else:
                cleaned_data['phone'] = phone
        
        # Optional referral code
        referral_code = data.get('referralCode', '').strip().upper()
        if referral_code:
            cleaned_data['referral_code'] = referral_code
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    @staticmethod
    def validate_login(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate user login data
        
        Args:
            data: Dictionary containing login data
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Email validation
        email = data.get('email', '').strip().lower()
        if not email:
            errors['email'] = 'Email is required'
        elif not AuthSchemas._validate_email_format(email):
            errors['email'] = 'Invalid email format'
        else:
            cleaned_data['email'] = email
        
        # Password validation
        password = data.get('password', '')
        if not password:
            errors['password'] = 'Password is required'
        else:
            cleaned_data['password'] = password
        
        # Optional remember me flag
        remember_me = data.get('rememberMe', False)
        cleaned_data['remember_me'] = bool(remember_me)
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    @staticmethod
    def validate_google_oauth(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate Google OAuth data
        
        Args:
            data: Dictionary containing OAuth data from Google
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Google ID token is required
        id_token = data.get('idToken', '').strip()
        if not id_token:
            errors['idToken'] = 'Google ID token is required'
        else:
            cleaned_data['id_token'] = id_token
        
        # Optional referral code for new users
        referral_code = data.get('referralCode', '').strip().upper()
        if referral_code:
            cleaned_data['referral_code'] = referral_code
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    @staticmethod
    def validate_password_reset_request(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate password reset request data
        
        Args:
            data: Dictionary containing reset request data
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Email validation
        email = data.get('email', '').strip().lower()
        if not email:
            errors['email'] = 'Email is required'
        elif not AuthSchemas._validate_email_format(email):
            errors['email'] = 'Invalid email format'
        else:
            cleaned_data['email'] = email
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    @staticmethod
    def validate_password_reset_confirm(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate password reset confirmation data
        
        Args:
            data: Dictionary containing reset confirmation data
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Reset token validation
        token = data.get('token', '').strip()
        if not token:
            errors['token'] = 'Reset token is required'
        else:
            cleaned_data['token'] = token
        
        # New password validation
        password = data.get('password', '')
        confirm_password = data.get('confirmPassword', '')
        
        if not password:
            errors['password'] = 'New password is required'
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        elif not AuthSchemas._validate_password_strength(password):
            errors['password'] = 'Password must contain at least one letter and one number'
        else:
            cleaned_data['password'] = password
        
        # Password confirmation
        if not confirm_password:
            errors['confirmPassword'] = 'Password confirmation is required'
        elif password != confirm_password:
            errors['confirmPassword'] = 'Passwords do not match'
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    @staticmethod
    def validate_token_refresh(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Validate token refresh data
        
        Args:
            data: Dictionary containing refresh token
            
        Returns:
            Tuple of (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Refresh token validation
        refresh_token = data.get('refreshToken', '').strip()
        if not refresh_token:
            errors['refreshToken'] = 'Refresh token is required'
        else:
            cleaned_data['refresh_token'] = refresh_token
        
        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None, cleaned_data if is_valid else None
    
    # Helper validation methods
    
    @staticmethod
    def _validate_email_format(email: str) -> bool:
        """Validate email format using regex"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def _validate_password_strength(password: str) -> bool:
        """
        Validate password strength
        Must contain at least one letter and one number
        """
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        return has_letter and has_number
    
    @staticmethod
    def _validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        # Remove common formatting characters, keeping + if present at start
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        # Check integrity
        if not cleaned: 
            return False
            
        # Allow leading +
        if cleaned.startswith('+'):
            digits = cleaned[1:]
        else:
            digits = cleaned
            
        return digits.isdigit() and 10 <= len(digits) <= 15
