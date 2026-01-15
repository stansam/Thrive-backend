from flask import request, current_app, url_for
from flask_jwt_extended import create_access_token, create_refresh_token
from app.extensions import db
from app.models import User
from app.models.enums import UserRole, SubscriptionTier
from app.api.auth.schemas import AuthSchemas
from app.utils.api_response import APIResponse
from app.utils.email import EmailService
from app.utils.referral import ReferralManager
from app.utils.audit_logging import AuditLogger
from app.services.notification import NotificationService
import uuid
import secrets

from app.api.auth import auth_bp

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    
    Request Body:
        {
            "fullName": "John Doe",
            "email": "john@example.com",
            "password": "SecurePass123",
            "confirmPassword": "SecurePass123",
            "phone": "+1234567890" (optional),
            "referralCode": "ABC123" (optional)
        }
    
    Returns:
        201: User created successfully with tokens
        400: Validation error
        409: Email already exists
    """
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, errors, cleaned_data = AuthSchemas.validate_registration(data)
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=cleaned_data['email']).first()
        if existing_user:
            return APIResponse.error('Email already registered', status_code=409)
        
        # Validate referral code if provided
        referrer_id = None
        if 'referral_code' in cleaned_data:
            referrer_id = ReferralManager.validate_referral_code(cleaned_data['referral_code'])
            if not referrer_id:
                return APIResponse.validation_error({'referralCode': 'Invalid referral code'})
        
        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            email=cleaned_data['email'],
            first_name=cleaned_data['first_name'],
            last_name=cleaned_data['last_name'],
            phone=cleaned_data.get('phone'),
            role=UserRole.CUSTOMER,
            subscription_tier=SubscriptionTier.NONE,
            referred_by=referrer_id,
            email_verified=False,
            is_active=True
        )
        
        # Set password
        user.set_password(cleaned_data['password'])
        
        # Generate unique referral code for new user
        user.referral_code = ReferralManager.generate_referral_code(user.id)
        
        # Save user
        db.session.add(user)
        db.session.commit()
        
        # Apply referral credit if applicable
        if referrer_id:
            try:
                ReferralManager.apply_referral(referrer_id, user.id)
            except Exception as e:
                current_app.logger.error(f"Failed to apply referral credit: {str(e)}")
        
        # Send verification email
        try:
            verification_token = secrets.token_urlsafe(32)
            # TODO: Store verification token with expiry in database or cache
            verification_url = url_for('auth.verify_email', token=verification_token, _external=True)
            
            EmailService.send_email(
                to=user.email,
                subject='Welcome to Thrive Travel - Verify Your Email',
                body=f"""
                Welcome to Thrive Travel, {user.first_name}!
                
                Please verify your email by clicking the link below:
                {verification_url}
                
                This link will expire in 24 hours.
                
                If you didn't create this account, please ignore this email.
                """
            )
        except Exception as e:
            current_app.logger.error(f"Failed to send verification email: {str(e)}")
        
        # Create welcome notification
        try:
            NotificationService.create_notification(
                user_id=user.id,
                notification_type='welcome',
                title='Welcome to Thrive Travel!',
                message='Your account has been successfully created. Start exploring amazing travel destinations!'
            )
        except Exception as e:
            current_app.logger.error(f"Failed to create notification: {str(e)}")
        
        # Log registration
        AuditLogger.log_action(
            user_id=user.id,
            action='user_registered',
            entity_type='user',
            entity_id=user.id,
            description=f'New user registered: {user.email}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Generate JWT tokens
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'email': user.email, 'role': user.role.value}
        )
        refresh_token = create_refresh_token(identity=user.id)
        
        return APIResponse.success(
            data={
                'user': user.to_dict(),
                'tokens': {
                    'accessToken': access_token,
                    'refreshToken': refresh_token,
                    'tokenType': 'Bearer'
                }
            },
            message='Registration successful! Please check your email to verify your account.',
            status_code=201
        )
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return APIResponse.error('An error occurred during registration. Please try again.')


@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """
    Verify user email with token
    
    URL Parameters:
        token: Email verification token
    
    Returns:
        200: Email verified successfully
        401: Invalid or expired token
    """
    try:
        # TODO: Verify email token from database/cache
        # For now, this is a placeholder
        
        return APIResponse.error(
            'Email verification token validation not fully implemented. Please implement token storage and validation.',
            status_code=501
        )
        
        # When implemented:
        # user_id = validate_email_token(token)
        # if not user_id:
        #     return APIResponse.unauthorized('Invalid or expired verification token')
        # 
        # user = User.query.get(user_id)
        # user.email_verified = True
        # db.session.commit()
        # 
        # return APIResponse.success(message='Email verified successfully')
        
    except Exception as e:
        current_app.logger.error(f"Email verification error: {str(e)}")
        return APIResponse.error('An error occurred. Please try again.')
