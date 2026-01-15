
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

from app.extensions import db
from app.models import User
from app.api.client.schemas import DashboardSchemas
from app.utils.api_response import APIResponse
from app.utils.audit_logging import AuditLogger

from app.api.client import client_bp

@client_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get user profile information
    
    Returns:
        200: User profile data
        401: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        profile_data = {
            'id': user.id,
            'email': user.email,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'phone': user.phone,
            'dateOfBirth': user.date_of_birth.isoformat() if user.date_of_birth else None,
            'passportNumber': user.passport_number,
            'passportExpiry': user.passport_expiry.isoformat() if user.passport_expiry else None,
            'nationality': user.nationality,
            'preferredAirline': user.preferred_airline,
            'frequentFlyerNumbers': user.frequent_flyer_numbers,
            'dietaryPreferences': user.dietary_preferences,
            'specialAssistance': user.special_assistance,
            'companyName': user.company_name,
            'companyTaxId': user.company_tax_id,
            'billingAddress': user.billing_address,
            'role': user.role.value,
            'subscriptionTier': user.subscription_tier.value,
            'referralCode': user.referral_code,
            'referralCredits': float(user.referral_credits),
            'emailVerified': user.email_verified,
            'createdAt': user.created_at.isoformat(),
            'lastLogin': user.last_login.isoformat() if user.last_login else None
        }
        
        return APIResponse.success(
            data={'profile': profile_data},
            message='Profile retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Get profile error: {str(e)}")
        return APIResponse.error('An error occurred while fetching profile data')


@client_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update user profile information
    
    Returns:
        200: Profile updated successfully
        400: Validation error
        401: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        data = request.get_json()
        
        # Validate input
        is_valid, errors, cleaned_data = DashboardSchemas.validate_profile_update(data)
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Update user fields
        for field, value in cleaned_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log profile update
        AuditLogger.log_action(
            user_id=user.id,
            action='profile_updated',
            entity_type='user',
            entity_id=user.id,
            description='User profile updated',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success(
            data={'profile': {
                'id': user.id,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'phone': user.phone
            }},
            message='Profile updated successfully'
        )
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update profile error: {str(e)}")
        return APIResponse.error('An error occurred while updating profile')
