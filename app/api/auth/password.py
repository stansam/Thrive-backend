from flask import request, current_app
from app.extensions import db
from app.models import User
from app.api.auth.schemas import AuthSchemas
from app.utils.api_response import APIResponse
from app.utils.email import EmailService
from app.utils.audit_logging import AuditLogger
import secrets

from app.api.auth import auth_bp

@auth_bp.route('/password-reset/request', methods=['POST'])
def request_password_reset():
    """
    Request password reset email
    
    Request Body:
        {
            "email": "john@example.com"
        }
    
    Returns:
        200: Reset email sent (always returns success for security)
    """
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, errors, cleaned_data = AuthSchemas.validate_password_reset_request(data)
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Find user (don't reveal if user exists)
        user = User.query.filter_by(email=cleaned_data['email']).first()
        
        if user and user.is_active:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            # TODO: Store reset token with expiry in database or cache (1 hour expiry)
            
            # Send reset email
            reset_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={reset_token}"
            
            try:
                EmailService.send_email(
                    to=user.email,
                    subject='Thrive Travel - Password Reset Request',
                    body=f"""
                    Hello {user.first_name},
                    
                    You requested to reset your password. Click the link below to reset it:
                    {reset_url}
                    
                    This link will expire in 1 hour.
                    
                    If you didn't request this, please ignore this email.
                    """
                )
                
                # Log password reset request
                AuditLogger.log_action(
                    user_id=user.id,
                    action='password_reset_requested',
                    description='Password reset requested',
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            except Exception as e:
                current_app.logger.error(f"Failed to send reset email: {str(e)}")
        
        # Always return success (security best practice)
        return APIResponse.success(
            message='If an account exists with that email, a password reset link has been sent.'
        )
        
    except Exception as e:
        current_app.logger.error(f"Password reset request error: {str(e)}")
        return APIResponse.error('An error occurred. Please try again.')


@auth_bp.route('/password-reset/confirm', methods=['POST'])
def confirm_password_reset():
    """
    Confirm password reset with token
    
    Request Body:
        {
            "token": "reset_token_here",
            "password": "NewSecurePass123",
            "confirmPassword": "NewSecurePass123"
        }
    
    Returns:
        200: Password reset successful
        400: Validation error
        401: Invalid or expired token
    """
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, errors, cleaned_data = AuthSchemas.validate_password_reset_confirm(data)
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # TODO: Verify reset token from database/cache
        # For now, this is a placeholder
        # In production, retrieve user_id from stored token
        
        # Placeholder: You would validate the token and get user_id
        # user_id = validate_reset_token(cleaned_data['token'])
        # if not user_id:
        #     return APIResponse.unauthorized('Invalid or expired reset token')
        
        # For demonstration, returning error
        return APIResponse.error(
            'Password reset token validation not fully implemented. Please implement token storage and validation.',
            status_code=501
        )
        
        # When implemented:
        # user = User.query.get(user_id)
        # user.set_password(cleaned_data['password'])
        # db.session.commit()
        # 
        # # Invalidate all existing tokens for this user
        # # Log password reset
        # AuditLogger.log_action(...)
        # 
        # return APIResponse.success(message='Password reset successful')
        
    except Exception as e:
        current_app.logger.error(f"Password reset confirm error: {str(e)}")
        return APIResponse.error('An error occurred. Please try again.')
