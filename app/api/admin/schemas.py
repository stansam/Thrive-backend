"""
Admin API Validation Schemas
Handles request validation for all admin endpoints
"""
from typing import Dict, Any, Tuple, Optional
import re
from datetime import datetime


class AdminSchemas:
    """Validation schemas for admin API endpoints"""
    
    # ===== User Management Schemas =====
    
    @staticmethod
    def validate_user_update(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
        """
        Validate user update request
        
        Returns:
            (is_valid, errors, cleaned_data)
        """
        errors = {}
        cleaned_data = {}
        
        # Optional fields
        if 'firstName' in data:
            first_name = str(data['firstName']).strip()
            if not first_name:
                errors['firstName'] = 'First name cannot be empty'
            else:
                cleaned_data['first_name'] = first_name
        
        if 'lastName' in data:
            last_name = str(data['lastName']).strip()
            if not last_name:
                errors['lastName'] = 'Last name cannot be empty'
            else:
                cleaned_data['last_name'] = last_name
        
        if 'phone' in data:
            cleaned_data['phone'] = str(data['phone']).strip() if data['phone'] else None
        
        if 'role' in data:
            valid_roles = ['customer', 'corporate', 'admin', 'agent']
            role = str(data['role']).lower()
            if role not in valid_roles:
                errors['role'] = f'Role must be one of: {", ".join(valid_roles)}'
            else:
                cleaned_data['role'] = role
        
        if 'subscriptionTier' in data:
            valid_tiers = ['none', 'bronze', 'silver', 'gold']
            tier = str(data['subscriptionTier']).lower()
            if tier not in valid_tiers:
                errors['subscriptionTier'] = f'Subscription tier must be one of: {", ".join(valid_tiers)}'
            else:
                cleaned_data['subscription_tier'] = tier
        
        if 'isActive' in data:
            cleaned_data['is_active'] = bool(data['isActive'])
        
        if 'emailVerified' in data:
            cleaned_data['email_verified'] = bool(data['emailVerified'])
        
        return len(errors) == 0, errors, cleaned_data
    
    # ===== Booking Management Schemas =====
    
    @staticmethod
    def validate_booking_update(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
        """Validate booking update request"""
        errors = {}
        cleaned_data = {}
        
        if 'status' in data:
            valid_statuses = ['pending', 'confirmed', 'cancelled', 'completed', 'refunded']
            status = str(data['status']).lower()
            if status not in valid_statuses:
                errors['status'] = f'Status must be one of: {", ".join(valid_statuses)}'
            else:
                cleaned_data['status'] = status
        
        if 'assignedAgentId' in data:
            cleaned_data['assigned_agent_id'] = str(data['assignedAgentId']).strip() if data['assignedAgentId'] else None
        
        if 'notes' in data:
            cleaned_data['notes'] = str(data['notes']).strip() if data['notes'] else None
        
        if 'airlineConfirmation' in data:
            cleaned_data['airline_confirmation'] = str(data['airlineConfirmation']).strip() if data['airlineConfirmation'] else None
        
        return len(errors) == 0, errors, cleaned_data
    
    @staticmethod
    def validate_booking_cancellation(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
        """Validate booking cancellation request"""
        errors = {}
        cleaned_data = {}
        
        if 'reason' not in data or not str(data['reason']).strip():
            errors['reason'] = 'Cancellation reason is required'
        else:
            cleaned_data['reason'] = str(data['reason']).strip()
        
        if 'refundAmount' in data:
            try:
                refund = float(data['refundAmount'])
                if refund < 0:
                    errors['refundAmount'] = 'Refund amount cannot be negative'
                else:
                    cleaned_data['refund_amount'] = refund
            except (ValueError, TypeError):
                errors['refundAmount'] = 'Invalid refund amount'
        
        return len(errors) == 0, errors, cleaned_data
    
    # ===== Quote Management Schemas =====
    
    @staticmethod
    def validate_quote_update(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
        """Validate quote update request"""
        errors = {}
        cleaned_data = {}
        
        if 'status' in data:
            valid_statuses = ['pending', 'sent', 'accepted', 'expired', 'rejected']
            status = str(data['status']).lower()
            if status not in valid_statuses:
                errors['status'] = f'Status must be one of: {", ".join(valid_statuses)}'
            else:
                cleaned_data['status'] = status
        
        if 'quotedPrice' in data:
            try:
                price = float(data['quotedPrice'])
                if price < 0:
                    errors['quotedPrice'] = 'Price cannot be negative'
                else:
                    cleaned_data['quoted_price'] = price
            except (ValueError, TypeError):
                errors['quotedPrice'] = 'Invalid price format'
        
        if 'serviceFee' in data:
            try:
                fee = float(data['serviceFee'])
                if fee < 0:
                    errors['serviceFee'] = 'Service fee cannot be negative'
                else:
                    cleaned_data['service_fee'] = fee
            except (ValueError, TypeError):
                errors['serviceFee'] = 'Invalid service fee format'
        
        if 'agentNotes' in data:
            cleaned_data['agent_notes'] = str(data['agentNotes']).strip() if data['agentNotes'] else None
        
        if 'quoteDetails' in data:
            cleaned_data['quote_details'] = data['quoteDetails']
        
        return len(errors) == 0, errors, cleaned_data
    
    # ===== Package Management Schemas =====
    
    @staticmethod
    def validate_package_create(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
        """Validate package creation request"""
        errors = {}
        cleaned_data = {}
        
        # Required fields
        required_fields = ['name', 'destinationCity', 'destinationCountry', 'durationDays', 'durationNights', 'startingPrice', 'pricePerPerson']
        
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                errors[field] = f'{field} is required'
        
        if errors:
            return False, errors, cleaned_data
        
        # Clean and validate fields
        cleaned_data['name'] = str(data['name']).strip()
        cleaned_data['destination_city'] = str(data['destinationCity']).strip()
        cleaned_data['destination_country'] = str(data['destinationCountry']).strip()
        
        # Generate slug from name
        slug = re.sub(r'[^\w\s-]', '', cleaned_data['name'].lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        cleaned_data['slug'] = slug
        
        try:
            cleaned_data['duration_days'] = int(data['durationDays'])
            cleaned_data['duration_nights'] = int(data['durationNights'])
        except (ValueError, TypeError):
            errors['duration'] = 'Duration must be valid numbers'
        
        try:
            cleaned_data['starting_price'] = float(data['startingPrice'])
            cleaned_data['price_per_person'] = float(data['pricePerPerson'])
        except (ValueError, TypeError):
            errors['price'] = 'Prices must be valid numbers'
        
        # Optional fields
        if 'description' in data:
            cleaned_data['full_description'] = str(data['description']).strip() if data['description'] else None
        
        if 'highlights' in data and isinstance(data['highlights'], list):
            cleaned_data['highlights'] = data['highlights']
        
        if 'inclusions' in data and isinstance(data['inclusions'], list):
            cleaned_data['inclusions'] = data['inclusions']
        
        if 'exclusions' in data and isinstance(data['exclusions'], list):
            cleaned_data['exclusions'] = data['exclusions']
        
        if 'itinerary' in data:
            cleaned_data['itinerary'] = data['itinerary']
        
        if 'hotelName' in data:
            cleaned_data['hotel_name'] = str(data['hotelName']).strip() if data['hotelName'] else None
        
        if 'hotelRating' in data:
            try:
                rating = int(data['hotelRating'])
                if 1 <= rating <= 5:
                    cleaned_data['hotel_rating'] = rating
            except (ValueError, TypeError):
                pass
        
        if 'featuredImage' in data:
            cleaned_data['featured_image'] = str(data['featuredImage']).strip() if data['featuredImage'] else None
        
        if 'galleryImages' in data and isinstance(data['galleryImages'], list):
            cleaned_data['gallery_images'] = data['galleryImages']
        
        if 'isActive' in data:
            cleaned_data['is_active'] = bool(data['isActive'])
        
        return len(errors) == 0, errors, cleaned_data
    
    @staticmethod
    def validate_package_update(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
        """Validate package update request"""
        errors = {}
        cleaned_data = {}
        
        # All fields are optional for update
        if 'name' in data:
            name = str(data['name']).strip()
            if name:
                cleaned_data['name'] = name
                # Regenerate slug
                slug = re.sub(r'[^\w\s-]', '', name.lower())
                slug = re.sub(r'[-\s]+', '-', slug)
                cleaned_data['slug'] = slug
        
        if 'description' in data:
            cleaned_data['full_description'] = str(data['description']).strip() if data['description'] else None
        
        if 'destinationCity' in data:
            cleaned_data['destination_city'] = str(data['destinationCity']).strip()
        
        if 'destinationCountry' in data:
            cleaned_data['destination_country'] = str(data['destinationCountry']).strip()
        
        if 'durationDays' in data:
            try:
                cleaned_data['duration_days'] = int(data['durationDays'])
            except (ValueError, TypeError):
                errors['durationDays'] = 'Duration days must be a number'
        
        if 'durationNights' in data:
            try:
                cleaned_data['duration_nights'] = int(data['durationNights'])
            except (ValueError, TypeError):
                errors['durationNights'] = 'Duration nights must be a number'
        
        if 'startingPrice' in data:
            try:
                cleaned_data['starting_price'] = float(data['startingPrice'])
            except (ValueError, TypeError):
                errors['startingPrice'] = 'Starting price must be a number'
        
        if 'pricePerPerson' in data:
            try:
                cleaned_data['price_per_person'] = float(data['pricePerPerson'])
            except (ValueError, TypeError):
                errors['pricePerPerson'] = 'Price per person must be a number'
        
        if 'highlights' in data and isinstance(data['highlights'], list):
            cleaned_data['highlights'] = data['highlights']
        
        if 'inclusions' in data and isinstance(data['inclusions'], list):
            cleaned_data['inclusions'] = data['inclusions']
        
        if 'exclusions' in data and isinstance(data['exclusions'], list):
            cleaned_data['exclusions'] = data['exclusions']
        
        if 'itinerary' in data:
            cleaned_data['itinerary'] = data['itinerary']
        
        if 'hotelName' in data:
            cleaned_data['hotel_name'] = str(data['hotelName']).strip() if data['hotelName'] else None
        
        if 'hotelRating' in data:
            try:
                rating = int(data['hotelRating'])
                if 1 <= rating <= 5:
                    cleaned_data['hotel_rating'] = rating
                else:
                    errors['hotelRating'] = 'Hotel rating must be between 1 and 5'
            except (ValueError, TypeError):
                errors['hotelRating'] = 'Hotel rating must be a number'
        
        if 'featuredImage' in data:
            cleaned_data['featured_image'] = str(data['featuredImage']).strip() if data['featuredImage'] else None
        
        if 'galleryImages' in data and isinstance(data['galleryImages'], list):
            cleaned_data['gallery_images'] = data['galleryImages']
        
        if 'isActive' in data:
            cleaned_data['is_active'] = bool(data['isActive'])
        
        return len(errors) == 0, errors, cleaned_data
    
    # ===== Payment Management Schemas =====
    
    @staticmethod
    def validate_payment_refund(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
        """Validate payment refund request"""
        errors = {}
        cleaned_data = {}
        
        if 'amount' not in data:
            errors['amount'] = 'Refund amount is required'
        else:
            try:
                amount = float(data['amount'])
                if amount <= 0:
                    errors['amount'] = 'Refund amount must be greater than 0'
                else:
                    cleaned_data['refund_amount'] = amount
            except (ValueError, TypeError):
                errors['amount'] = 'Invalid refund amount'
        
        if 'reason' not in data or not str(data['reason']).strip():
            errors['reason'] = 'Refund reason is required'
        else:
            cleaned_data['refund_reason'] = str(data['reason']).strip()
        
        return len(errors) == 0, errors, cleaned_data
    
    # ===== Contact Message Schemas =====
    
    @staticmethod
    def validate_contact_message_update(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
        """Validate contact message update request"""
        errors = {}
        cleaned_data = {}
        
        if 'status' in data:
            valid_statuses = ['new', 'in_progress', 'resolved']
            status = str(data['status']).lower()
            if status not in valid_statuses:
                errors['status'] = f'Status must be one of: {", ".join(valid_statuses)}'
            else:
                cleaned_data['status'] = status
        
        if 'priority' in data:
            valid_priorities = ['low', 'normal', 'high', 'urgent']
            priority = str(data['priority']).lower()
            if priority not in valid_priorities:
                errors['priority'] = f'Priority must be one of: {", ".join(valid_priorities)}'
            else:
                cleaned_data['priority'] = priority
        
        if 'assignedTo' in data:
            cleaned_data['assigned_to'] = str(data['assignedTo']).strip() if data['assignedTo'] else None
        
        if 'adminNotes' in data:
            cleaned_data['admin_notes'] = str(data['adminNotes']).strip() if data['adminNotes'] else None
        
        return len(errors) == 0, errors, cleaned_data
    
    # ===== Pagination & Filtering Schemas =====
    
    @staticmethod
    def validate_pagination(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean pagination parameters"""
        page = 1
        per_page = 20
        
        if 'page' in data:
            try:
                page = max(1, int(data['page']))
            except (ValueError, TypeError):
                pass
        
        if 'perPage' in data:
            try:
                per_page = min(100, max(1, int(data['perPage'])))
            except (ValueError, TypeError):
                pass
        
        return {'page': page, 'per_page': per_page}
    
    @staticmethod
    def validate_date_range(data: Dict[str, Any]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Validate and parse date range parameters"""
        start_date = None
        end_date = None
        
        if 'startDate' in data and data['startDate']:
            try:
                start_date = datetime.fromisoformat(str(data['startDate']).replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
        
        if 'endDate' in data and data['endDate']:
            try:
                end_date = datetime.fromisoformat(str(data['endDate']).replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
        
        return start_date, end_date
