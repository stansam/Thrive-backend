from flask import current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User
from app.utils.api_response import APIResponse

from app.api.auth import auth_bp

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: Current user data
        401: Invalid or expired token
    """
    try:
        # Get current user ID from JWT
        current_user_id = get_jwt_identity()
        
        # Get user from database
        user = User.query.get(current_user_id)
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        return APIResponse.success(
            data={'user': user.to_dict()},
            message='User retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Get current user error: {str(e)}")
        return APIResponse.error('An error occurred. Please try again.')
