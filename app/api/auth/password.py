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
            # Generate secure token
            from itsdangerous import URLSafeTimedSerializer
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            reset_token = s.dumps(user.email, salt='password-reset-salt')
            
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
        
        token = cleaned_data['token']
        new_password = cleaned_data['password']
        
        # Verify token
        from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        
        try:
            # Token valid for 1 hour (3600 seconds)
            email = s.loads(token, salt='password-reset-salt', max_age=3600)
        except SignatureExpired:
            return APIResponse.unauthorized('The password reset link has expired.')
        except BadSignature:
            return APIResponse.unauthorized('Invalid password reset token.')
            
        user = User.query.filter_by(email=email).first()
        if not user:
            return APIResponse.unauthorized('User not found.')
            
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        # Log successful reset
        AuditLogger.log_action(
            user_id=user.id,
            action='password_reset_success',
            description='Password reset successfully using email token',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success(message='Password reset successful. You can now login with your new password.')
        
    except Exception as e:
        current_app.logger.error(f"Password reset confirm error: {str(e)}")
        # Don't expose internal errors unless necessary, but logging is key
        return APIResponse.error('An error occurred while resetting your password.')
