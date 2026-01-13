
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import User
from app.api.client.schemas import DashboardSchemas
from app.utils.api_response import APIResponse
from app.utils.audit_logging import AuditLogger

from . import client_bp

@client_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_settings():
    """
    Get user settings/preferences
    
    Returns:
        200: User settings object
        401: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
            
        # Default settings if none exist
        default_settings = {
            'emailNotifications': True,
            'marketingEmails': False,
            'smsNotifications': False,
            'profileVisibility': False,
            'dataSharing': False
        }
        
        # Merge saved settings with defaults
        user_settings = user.custom_settings or {}
        merged_settings = {**default_settings, **user_settings}
        
        return APIResponse.success(
            data={'settings': merged_settings},
            message='Settings retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Get settings error: {str(e)}")
        return APIResponse.error('An error occurred while fetching settings')

@client_bp.route('/settings', methods=['PUT'])
@jwt_required()
def update_settings():
    """
    Update user settings
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
            
        data = request.get_json()
        
        # Validate settings
        is_valid, errors, cleaned_data = DashboardSchemas.validate_settings_update(data)
        if not is_valid:
            return APIResponse.validation_error(errors)
            
        # Update user settings
        # We merge with existing to avoid losing other keys if future settings are added
        current_settings = user.custom_settings or {}
        updated_settings = {**current_settings, **cleaned_data}
        
        user.custom_settings = updated_settings
        db.session.commit()
        
        return APIResponse.success(
            data={'settings': updated_settings},
            message='Settings updated successfully'
        )
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update settings error: {str(e)}")
        return APIResponse.error('An error occurred while updating settings')
