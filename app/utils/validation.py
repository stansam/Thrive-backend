from flask import jsonify, current_app
from functools import wraps
from flask_login import current_user
from datetime import datetime, timedelta


class Validator:
    """Input validation helpers"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        # Remove common formatting characters
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        # Check if it's 10-15 digits
        return cleaned.isdigit() and 10 <= len(cleaned) <= 15
    
    @staticmethod
    def validate_passport_number(passport: str) -> bool:
        """Validate passport number format"""
        # Basic validation: 6-9 alphanumeric characters
        return bool(re.match(r'^[A-Z0-9]{6,9}$', passport.upper()))
    
    @staticmethod
    def validate_date_of_birth(dob: datetime, min_age: int = 0, max_age: int = 150) -> Tuple[bool, str]:
        """Validate date of birth"""
        today = datetime.utcnow().date()
        
        if dob > today:
            return False, "Date of birth cannot be in the future"
        
        age = (today - dob).days // 365
        
        if age < min_age:
            return False, f"Must be at least {min_age} years old"
        
        if age > max_age:
            return False, f"Invalid date of birth"
        
        return True, "Valid date of birth"
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = None) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text