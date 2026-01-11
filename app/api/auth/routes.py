"""
Authentication Routes
Handles user registration, login, OAuth, password reset, and token management
"""
from flask import Blueprint, request, jsonify, current_app, url_for
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from datetime import datetime, timedelta, timezone
import secrets
import uuid

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.extensions import db
from app.models import User
from app.models.revoked_tokens import RevokedToken
from app.models.enums import UserRole, SubscriptionTier
from app.api.auth.schemas import AuthSchemas
from app.utils.api_response import APIResponse
from app.utils.email import EmailService
from app.utils.referral import ReferralManager
from app.utils.audit_logging import AuditLogger
from app.services.notification import NotificationService

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Token blacklist (in production, use Redis)
token_blacklist = set()


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


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user with email and password
    
    Request Body:
        {
            "email": "john@example.com",
            "password": "SecurePass123",
            "rememberMe": false (optional)
        }
    
    Returns:
        200: Login successful with tokens
        400: Validation error
        401: Invalid credentials
    """
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, errors, cleaned_data = AuthSchemas.validate_login(data)
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Find user by email
        user = User.query.filter_by(email=cleaned_data['email']).first()
        
        # Check if user exists and password is correct
        if not user or not user.check_password(cleaned_data['password']):
            # Log failed attempt
            if user:
                AuditLogger.log_action(
                    user_id=user.id,
                    action='login_failed',
                    description='Failed login attempt - invalid password',
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            return APIResponse.unauthorized('Invalid email or password')
        
        # Check if account is active
        if not user.is_active:
            return APIResponse.forbidden('Your account has been deactivated. Please contact support.')
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log successful login
        AuditLogger.log_action(
            user_id=user.id,
            action='user_login',
            description=f'User logged in: {user.email}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Generate JWT tokens
        expires_delta = timedelta(days=30) if cleaned_data.get('remember_me') else timedelta(hours=1)
        
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'email': user.email, 'role': user.role.value},
            expires_delta=timedelta(minutes=15)
        )
        refresh_token = create_refresh_token(
            identity=user.id,
            expires_delta=expires_delta
        )
        
        return APIResponse.success(
            data={
                'user': user.to_dict(),
                'tokens': {
                    'accessToken': access_token,
                    'refreshToken': refresh_token,
                    'tokenType': 'Bearer'
                }
            },
            message='Login successful'
        )
        
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return APIResponse.error('An error occurred during login. Please try again.')


@auth_bp.route('/google', methods=['POST'])
def google_oauth():
    """
    Login or register user with Google OAuth
    
    Request Body:
        {
            "idToken": "google_id_token_here",
            "referralCode": "ABC123" (optional, for new users)
        }
    
    Returns:
        200: Login/Registration successful with tokens
        400: Validation error
        401: Invalid Google token
    """
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, errors, cleaned_data = AuthSchemas.validate_google_oauth(data)
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Verify Google ID token
        try:
            # Get Google Client ID from config
            google_client_id = current_app.config.get('GOOGLE_CLIENT_ID')
            if not google_client_id:
                return APIResponse.error('Google OAuth is not configured')
            
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                cleaned_data['id_token'],
                google_requests.Request(),
                google_client_id
            )
            
            # Extract user info from Google
            google_email = idinfo.get('email')
            google_name = idinfo.get('name', '')
            google_picture = idinfo.get('picture')
            email_verified = idinfo.get('email_verified', False)
            
            if not google_email:
                return APIResponse.error('Unable to retrieve email from Google')
            
        except ValueError as e:
            current_app.logger.error(f"Invalid Google token: {str(e)}")
            return APIResponse.unauthorized('Invalid Google token')
        
        # Check if user exists
        user = User.query.filter_by(email=google_email).first()
        
        if user:
            # Existing user - login
            if not user.is_active:
                return APIResponse.forbidden('Your account has been deactivated')
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            
            action = 'google_login'
            message = 'Login successful'
            
        else:
            # New user - register
            # Validate referral code if provided
            referrer_id = None
            if 'referral_code' in cleaned_data:
                referrer_id = ReferralManager.validate_referral_code(cleaned_data['referral_code'])
                if not referrer_id:
                    return APIResponse.validation_error({'referralCode': 'Invalid referral code'})
            
            # Split name
            name_parts = google_name.split(None, 1)
            first_name = name_parts[0] if name_parts else 'User'
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Create new user
            user = User(
                id=str(uuid.uuid4()),
                email=google_email,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.CUSTOMER,
                subscription_tier=SubscriptionTier.NONE,
                referred_by=referrer_id,
                email_verified=email_verified,
                is_active=True,
                password_hash='google_oauth'  # Placeholder for OAuth users
            )
            
            # Generate referral code
            user.referral_code = ReferralManager.generate_referral_code(user.id)
            
            db.session.add(user)
            db.session.commit()
            
            # Apply referral credit
            if referrer_id:
                try:
                    ReferralManager.apply_referral(referrer_id, user.id)
                except Exception as e:
                    current_app.logger.error(f"Failed to apply referral credit: {str(e)}")
            
            # Create welcome notification
            try:
                NotificationService.create_notification(
                    user_id=user.id,
                    notification_type='welcome',
                    title='Welcome to Thrive Travel!',
                    message='Your account has been successfully created via Google. Start exploring!'
                )
            except Exception as e:
                current_app.logger.error(f"Failed to create notification: {str(e)}")
            
            action = 'google_register'
            message = 'Registration successful via Google'
        
        # Log action
        AuditLogger.log_action(
            user_id=user.id,
            action=action,
            description=f'User {action} via Google OAuth: {user.email}',
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
            message=message
        )
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Google OAuth error: {str(e)}")
        return APIResponse.error('An error occurred during Google authentication')


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token
    
    Headers:
        Authorization: Bearer <refresh_token>
    
    Returns:
        200: New access token
        401: Invalid or expired refresh token
    """
    try:
        # Get current user from refresh token
        current_user_id = get_jwt_identity()
        
        # Check if token is blacklisted
        jwt_payload = get_jwt()
        jti = jwt_payload['jti']
        if RevokedToken.is_revoked(jti):
            return APIResponse.unauthorized('Token has been revoked')
        
        # Get user
        user = User.query.get(current_user_id)
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        new_refresh_token = create_refresh_token(identity=user.id)
        
        try:
            revoked = RevokedToken(jti=jti, type='refresh')
            db.session.add(revoked)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # If we can't revoke it (already revoked), then this request is using a stale/used token.
            return APIResponse.unauthorized('Token has already been used')

        # Generate new access token
        new_access_token = create_access_token(
            identity=user.id,
            additional_claims={'email': user.email, 'role': user.role.value}
        )
        
        return APIResponse.success(
            data={
                'tokens': {
                    'accessToken': new_access_token,
                    'refreshToken': new_refresh_token,
                    'tokenType': 'Bearer'
                }
            },
            message='Token refreshed successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return APIResponse.error('An error occurred during token refresh')


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user and blacklist token
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: Logout successful
    """
    try:
        # Get token JTI and add to blacklist
        jti = get_jwt()['jti']
        token_blacklist.add(jti)
        
        # Log logout
        current_user_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=current_user_id,
            action='user_logout',
            description='User logged out',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success(message='Logout successful')
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return APIResponse.error('An error occurred during logout')


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
