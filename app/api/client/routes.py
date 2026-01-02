"""
Dashboard Client API Routes
Handles all client-facing dashboard functionality including profile, bookings, subscriptions, and support
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import and_, or_, func

from app.extensions import db
from app.models import User, Booking, Package, Payment, Notification, Settings
from app.models.enums import BookingStatus, PaymentStatus, SubscriptionTier, UserRole
from app.api.client.schemas import DashboardSchemas
from app.utils.api_response import APIResponse
from app.utils.email import EmailService
from app.utils.audit_logging import AuditLogger
from app.services.notification import NotificationService

# Stripe integration
import stripe
import os

# Create blueprint
client_bp = Blueprint('client', __name__, url_prefix='/api/client/dashboard')


@client_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_dashboard_summary():
    """
    Get dashboard summary statistics
    
    Returns:
        200: Dashboard summary data including stats, recent bookings, and chart data
        401: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Get booking statistics
        total_bookings = Booking.query.filter_by(user_id=current_user_id).count()
        
        confirmed_bookings = Booking.query.filter_by(
            user_id=current_user_id,
            status=BookingStatus.CONFIRMED
        ).count()
        
        # Calculate total spent
        total_spent = db.session.query(func.sum(Payment.amount)).filter(
            Payment.user_id == current_user_id,
            Payment.status == PaymentStatus.PAID
        ).scalar() or Decimal('0.00')
        
        # Get upcoming bookings (next 30 days)
        upcoming_date = datetime.now(timezone.utc) + timedelta(days=30)
        upcoming_bookings = Booking.query.filter(
            and_(
                Booking.user_id == current_user_id,
                Booking.departure_date >= datetime.now(timezone.utc),
                Booking.departure_date <= upcoming_date,
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING])
            )
        ).count()
        
        # Get active trips (package tours)
        active_trips = Booking.query.filter(
            and_(
                Booking.user_id == current_user_id,
                Booking.booking_type == 'package',
                Booking.status == BookingStatus.CONFIRMED,
                Booking.departure_date >= datetime.now(timezone.utc)
            )
        ).count()
        
        # Get recent bookings (last 5)
        recent_bookings = Booking.query.filter_by(
            user_id=current_user_id
        ).order_by(Booking.created_at.desc()).limit(5).all()
        
        # Get monthly spending data for chart (last 12 months)
        chart_data = []
        for i in range(11, -1, -1):
            month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30*i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            monthly_total = db.session.query(func.sum(Payment.amount)).filter(
                and_(
                    Payment.user_id == current_user_id,
                    Payment.status == PaymentStatus.PAID,
                    Payment.paid_at >= month_start,
                    Payment.paid_at <= month_end
                )
            ).scalar() or Decimal('0.00')
            
            chart_data.append({
                'name': month_start.strftime('%b'),
                'total': float(monthly_total)
            })
        
        # Get unread notifications count
        unread_notifications = Notification.query.filter_by(
            user_id=current_user_id,
            is_read=False
        ).count()
        
        return APIResponse.success(
            data={
                'stats': {
                    'totalBookings': total_bookings,
                    'confirmedBookings': confirmed_bookings,
                    'totalSpent': float(total_spent),
                    'upcomingBookings': upcoming_bookings,
                    'activeTrips': active_trips,
                    'unreadNotifications': unread_notifications
                },
                'recentBookings': [booking.to_dict() for booking in recent_bookings],
                'chartData': chart_data,
                'subscriptionTier': user.subscription_tier.value,
                'hasActiveSubscription': user.has_active_subscription()
            },
            message='Dashboard summary retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Dashboard summary error: {str(e)}")
        return APIResponse.error('An error occurred while fetching dashboard data')


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
    
    Request Body:
        {
            "firstName": "John",
            "lastName": "Doe",
            "phone": "+1234567890",
            "dateOfBirth": "1990-01-01",
            "passportNumber": "AB123456",
            "passportExpiry": "2030-01-01",
            "nationality": "American",
            "preferredAirline": "Delta",
            "frequentFlyerNumbers": {"Delta": "123456"},
            "dietaryPreferences": "Vegetarian",
            "specialAssistance": "Wheelchair",
            "companyName": "Acme Corp",
            "companyTaxId": "123-45-6789",
            "billingAddress": "123 Main St"
        }
    
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


@client_bp.route('/subscriptions', methods=['GET'])
@jwt_required()
def get_subscriptions():
    """
    Get user subscription information
    
    Returns:
        200: Subscription data including current tier, usage, and available tiers
        401: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Define subscription tiers with pricing and benefits
        subscription_tiers = {
            'bronze': {
                'name': 'Bronze',
                'price': 29.99,
                'currency': 'USD',
                'interval': 'month',
                'maxBookings': 6,
                'benefits': [
                    '6 bookings per month',
                    'Basic customer support',
                    '5% discount on all bookings',
                    'Email notifications'
                ]
            },
            'silver': {
                'name': 'Silver',
                'price': 59.99,
                'currency': 'USD',
                'interval': 'month',
                'maxBookings': 15,
                'benefits': [
                    '15 bookings per month',
                    'Priority customer support',
                    '10% discount on all bookings',
                    'SMS & Email notifications',
                    'Free cancellation (up to 24h)'
                ]
            },
            'gold': {
                'name': 'Gold',
                'price': 99.99,
                'currency': 'USD',
                'interval': 'month',
                'maxBookings': -1,  # Unlimited
                'benefits': [
                    'Unlimited bookings',
                    '24/7 VIP customer support',
                    '15% discount on all bookings',
                    'SMS & Email notifications',
                    'Free cancellation anytime',
                    'Dedicated travel agent',
                    'Exclusive deals and offers'
                ]
            }
        }
        
        current_subscription = {
            'tier': user.subscription_tier.value,
            'startDate': user.subscription_start.isoformat() if user.subscription_start else None,
            'endDate': user.subscription_end.isoformat() if user.subscription_end else None,
            'isActive': user.has_active_subscription(),
            'bookingsUsed': user.monthly_bookings_used,
            'bookingsRemaining': subscription_tiers.get(user.subscription_tier.value, {}).get('maxBookings', 0) - user.monthly_bookings_used if user.subscription_tier.value != 'none' else 0
        }
        
        return APIResponse.success(
            data={
                'currentSubscription': current_subscription,
                'availableTiers': subscription_tiers
            },
            message='Subscription information retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Get subscriptions error: {str(e)}")
        return APIResponse.error('An error occurred while fetching subscription data')


@client_bp.route('/subscriptions/upgrade', methods=['POST'])
@jwt_required()
def upgrade_subscription():
    """
    Upgrade user subscription with Stripe payment
    
    Request Body:
        {
            "tier": "silver",
            "paymentMethodId": "pm_xxxxx"  # Stripe payment method ID
        }
    
    Returns:
        200: Subscription upgraded successfully
        400: Validation error
        401: Unauthorized
        402: Payment required/failed
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        data = request.get_json()
        
        # Validate input
        is_valid, errors, cleaned_data = DashboardSchemas.validate_subscription_upgrade(data)
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        tier = cleaned_data['tier']
        payment_method_id = cleaned_data.get('payment_method_id')
        
        # Define pricing
        tier_pricing = {
            'bronze': 2999,  # $29.99 in cents
            'silver': 5999,  # $59.99 in cents
            'gold': 9999     # $99.99 in cents
        }
        
        amount = tier_pricing.get(tier)
        if not amount:
            return APIResponse.error('Invalid subscription tier')
        
        # Initialize Stripe
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        
        if not stripe.api_key:
            return APIResponse.error('Payment processing is not configured. Please contact support.')
        
        try:
            # Create or retrieve Stripe customer
            if not hasattr(user, 'stripe_customer_id') or not user.stripe_customer_id:
                # Create new Stripe customer
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.get_full_name(),
                    metadata={'user_id': user.id}
                )
                # Note: You'll need to add stripe_customer_id field to User model
                # user.stripe_customer_id = customer.id
                customer_id = customer.id
            else:
                customer_id = user.stripe_customer_id
            
            # Attach payment method to customer if provided
            if payment_method_id:
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=customer_id
                )
                
                # Set as default payment method
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={'default_payment_method': payment_method_id}
                )
            
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',
                customer=customer_id,
                payment_method=payment_method_id,
                confirm=True,
                automatic_payment_methods={'enabled': True, 'allow_redirects': 'never'} if not payment_method_id else None,
                description=f'Subscription upgrade to {tier.upper()}',
                metadata={
                    'user_id': user.id,
                    'subscription_tier': tier,
                    'type': 'subscription'
                }
            )
            
            # Check payment status
            if payment_intent.status == 'succeeded':
                # Update user subscription
                user.subscription_tier = SubscriptionTier[tier.upper()]
                user.subscription_start = datetime.now(timezone.utc)
                user.subscription_end = datetime.now(timezone.utc) + timedelta(days=30)
                user.monthly_bookings_used = 0
                
                # Create payment record
                payment = Payment(
                    payment_reference=f'SUB-{payment_intent.id}',
                    user_id=user.id,
                    booking_id=None,  # Subscription payment, not booking
                    amount=Decimal(amount) / 100,
                    currency='USD',
                    payment_method='stripe',
                    status=PaymentStatus.PAID,
                    stripe_payment_intent_id=payment_intent.id,
                    stripe_charge_id=payment_intent.charges.data[0].id if payment_intent.charges.data else None,
                    paid_at=datetime.now(timezone.utc)
                )
                
                db.session.add(payment)
                db.session.commit()
                
                # Send confirmation email
                try:
                    EmailService.send_email(
                        to=user.email,
                        subject=f'Subscription Upgraded to {tier.upper()}',
                        body=f"""
                        Hello {user.first_name},
                        
                        Your subscription has been successfully upgraded to {tier.upper()}!
                        
                        Your new subscription is active and will renew on {user.subscription_end.strftime('%B %d, %Y')}.
                        
                        Thank you for choosing Thrive Travel!
                        """
                    )
                except Exception as e:
                    current_app.logger.error(f"Failed to send subscription email: {str(e)}")
                
                # Create notification
                try:
                    NotificationService.create_notification(
                        user_id=user.id,
                        notification_type='subscription_upgraded',
                        title='Subscription Upgraded!',
                        message=f'Your subscription has been upgraded to {tier.upper()}. Enjoy your new benefits!'
                    )
                except Exception as e:
                    current_app.logger.error(f"Failed to create notification: {str(e)}")
                
                # Log subscription upgrade
                AuditLogger.log_action(
                    user_id=user.id,
                    action='subscription_upgraded',
                    entity_type='subscription',
                    entity_id=payment.id,
                    description=f'Subscription upgraded to {tier.upper()}',
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                
                return APIResponse.success(
                    data={
                        'subscription': {
                            'tier': user.subscription_tier.value,
                            'startDate': user.subscription_start.isoformat(),
                            'endDate': user.subscription_end.isoformat()
                        },
                        'payment': {
                            'id': payment.id,
                            'amount': float(payment.amount),
                            'status': payment.status.value
                        }
                    },
                    message='Subscription upgraded successfully!'
                )
            else:
                return APIResponse.error(
                    f'Payment {payment_intent.status}. Please try again or contact support.',
                    status_code=402
                )
                
        except stripe.error.CardError as e:
            return APIResponse.error(f'Payment failed: {e.user_message}', status_code=402)
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return APIResponse.error('Payment processing error. Please try again.')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Subscription upgrade error: {str(e)}")
        return APIResponse.error('An error occurred while upgrading subscription')


@client_bp.route('/bookings', methods=['GET'])
@jwt_required()
def get_bookings():
    """
    Get user bookings with filters and pagination
    
    Query Parameters:
        status: Filter by booking status (pending, confirmed, cancelled, completed, refunded, all)
        type: Filter by booking type (flight, package, hotel, custom, all)
        startDate: Filter bookings from this date (YYYY-MM-DD)
        endDate: Filter bookings until this date (YYYY-MM-DD)
        page: Page number (default: 1)
        perPage: Items per page (default: 10, max: 100)
    
    Returns:
        200: Paginated list of bookings
        400: Validation error
        401: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Get query parameters
        params = {
            'status': request.args.get('status', '').strip(),
            'type': request.args.get('type', '').strip(),
            'startDate': request.args.get('startDate', '').strip(),
            'endDate': request.args.get('endDate', '').strip(),
            'page': request.args.get('page', 1),
            'perPage': request.args.get('perPage', 10)
        }
        
        # Validate filters
        is_valid, errors, cleaned_data = DashboardSchemas.validate_booking_filters(params)
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Build query
        query = Booking.query.filter_by(user_id=current_user_id)
        
        # Apply filters
        if cleaned_data.get('status'):
            query = query.filter_by(status=BookingStatus[cleaned_data['status'].upper()])
        
        if cleaned_data.get('booking_type'):
            query = query.filter_by(booking_type=cleaned_data['booking_type'])
        
        if cleaned_data.get('start_date'):
            query = query.filter(Booking.departure_date >= cleaned_data['start_date'])
        
        if cleaned_data.get('end_date'):
            query = query.filter(Booking.departure_date <= cleaned_data['end_date'])
        
        # Order by creation date (newest first)
        query = query.order_by(Booking.created_at.desc())
        
        # Paginate
        page = cleaned_data.get('page', 1)
        per_page = cleaned_data.get('per_page', 10)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        bookings_data = []
        for booking in pagination.items:
            booking_dict = booking.to_dict()
            
            # Add passenger count
            booking_dict['passengerCount'] = booking.get_total_passengers()
            
            # Add payment status
            latest_payment = Payment.query.filter_by(booking_id=booking.id).order_by(Payment.created_at.desc()).first()
            booking_dict['paymentStatus'] = latest_payment.status.value if latest_payment else 'pending'
            
            bookings_data.append(booking_dict)
        
        return APIResponse.success(
            data={
                'bookings': bookings_data,
                'pagination': {
                    'page': pagination.page,
                    'perPage': pagination.per_page,
                    'totalPages': pagination.pages,
                    'totalItems': pagination.total,
                    'hasNext': pagination.has_next,
                    'hasPrev': pagination.has_prev
                }
            },
            message='Bookings retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Get bookings error: {str(e)}")
        return APIResponse.error('An error occurred while fetching bookings')


@client_bp.route('/bookings/<booking_id>', methods=['GET'])
@jwt_required()
def get_booking_details(booking_id):
    """
    Get detailed booking information
    
    Returns:
        200: Booking details including passengers and payments
        401: Unauthorized
        404: Booking not found
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Get booking
        booking = Booking.query.filter_by(id=booking_id, user_id=current_user_id).first()
        
        if not booking:
            return APIResponse.not_found('Booking not found')
        
        # Get booking details
        booking_dict = booking.to_dict()
        
        # Add passengers
        passengers = []
        for passenger in booking.passengers:
            passengers.append({
                'id': passenger.id,
                'firstName': passenger.first_name,
                'lastName': passenger.last_name,
                'dateOfBirth': passenger.date_of_birth.isoformat() if passenger.date_of_birth else None,
                'passportNumber': passenger.passport_number,
                'nationality': passenger.nationality,
                'passengerType': passenger.passenger_type
            })
        
        booking_dict['passengers'] = passengers
        
        # Add payments
        payments = []
        for payment in booking.payments:
            payments.append({
                'id': payment.id,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'status': payment.status.value,
                'paymentMethod': payment.payment_method,
                'paidAt': payment.paid_at.isoformat() if payment.paid_at else None,
                'createdAt': payment.created_at.isoformat()
            })
        
        booking_dict['payments'] = payments
        
        # Add package details if applicable
        if booking.package_id:
            package = Package.query.get(booking.package_id)
            if package:
                booking_dict['package'] = {
                    'id': package.id,
                    'name': package.name,
                    'destination': f"{package.destination_city}, {package.destination_country}",
                    'duration': f"{package.duration_days} Days / {package.duration_nights} Nights",
                    'hotelName': package.hotel_name,
                    'hotelRating': package.hotel_rating
                }
        
        return APIResponse.success(
            data={'booking': booking_dict},
            message='Booking details retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Get booking details error: {str(e)}")
        return APIResponse.error('An error occurred while fetching booking details')


@client_bp.route('/bookings/<booking_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_booking(booking_id):
    """
    Cancel a booking
    
    Request Body:
        {
            "reason": "Change of plans",
            "requestRefund": true
        }
    
    Returns:
        200: Booking cancelled successfully
        400: Validation error or booking cannot be cancelled
        401: Unauthorized
        404: Booking not found
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Get booking
        booking = Booking.query.filter_by(id=booking_id, user_id=current_user_id).first()
        
        if not booking:
            return APIResponse.not_found('Booking not found')
        
        # Check if booking can be cancelled
        if booking.status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED, BookingStatus.REFUNDED]:
            return APIResponse.error(f'Cannot cancel booking with status: {booking.status.value}')
        
        data = request.get_json() or {}
        
        # Validate input
        is_valid, errors, cleaned_data = DashboardSchemas.validate_booking_cancellation(data)
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Update booking status
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now(timezone.utc)
        booking.notes = f"Cancelled by user. Reason: {cleaned_data.get('reason', 'Not specified')}"
        
        # Handle refund if requested
        refund_amount = Decimal('0.00')
        if cleaned_data.get('request_refund', True):
            # Calculate refund based on cancellation policy
            # For simplicity, we'll refund 100% if cancelled 24h before departure
            if booking.departure_date:
                hours_until_departure = (booking.departure_date - datetime.now(timezone.utc)).total_seconds() / 3600
                
                if hours_until_departure >= 24:
                    refund_percentage = 1.0  # 100% refund
                elif hours_until_departure >= 12:
                    refund_percentage = 0.5  # 50% refund
                else:
                    refund_percentage = 0.0  # No refund
                
                # Check subscription tier for better refund policy
                if user.subscription_tier in [SubscriptionTier.SILVER, SubscriptionTier.GOLD]:
                    refund_percentage = 1.0  # Full refund for premium members
                
                refund_amount = booking.total_price * Decimal(str(refund_percentage))
                
                # Find the payment to refund
                payment = Payment.query.filter_by(
                    booking_id=booking.id,
                    status=PaymentStatus.PAID
                ).first()
                
                if payment and refund_amount > 0:
                    # Process refund via Stripe if payment was made with Stripe
                    if payment.stripe_charge_id:
                        try:
                            stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
                            refund = stripe.Refund.create(
                                charge=payment.stripe_charge_id,
                                amount=int(refund_amount * 100)  # Convert to cents
                            )
                            
                            payment.refund_amount = refund_amount
                            payment.status = PaymentStatus.REFUNDED
                            payment.refunded_at = datetime.now(timezone.utc)
                            booking.status = BookingStatus.REFUNDED
                        except stripe.error.StripeError as e:
                            current_app.logger.error(f"Stripe refund error: {str(e)}")
                            # Continue with cancellation even if refund fails
                    else:
                        # Manual refund processing
                        payment.refund_amount = refund_amount
                        payment.refund_reason = cleaned_data.get('reason', 'Booking cancelled')
        
        db.session.commit()
        
        # Send cancellation email
        try:
            EmailService.send_email(
                to=user.email,
                subject=f'Booking Cancelled - {booking.booking_reference}',
                body=f"""
                Hello {user.first_name},
                
                Your booking {booking.booking_reference} has been cancelled.
                
                Refund Amount: ${float(refund_amount):.2f}
                
                If you have any questions, please contact our support team.
                
                Thank you for using Thrive Travel.
                """
            )
        except Exception as e:
            current_app.logger.error(f"Failed to send cancellation email: {str(e)}")
        
        # Create notification
        try:
            NotificationService.create_notification(
                user_id=user.id,
                notification_type='booking_cancelled',
                title='Booking Cancelled',
                message=f'Your booking {booking.booking_reference} has been cancelled. Refund: ${float(refund_amount):.2f}',
                booking_id=booking.id
            )
        except Exception as e:
            current_app.logger.error(f"Failed to create notification: {str(e)}")
        
        # Log cancellation
        AuditLogger.log_action(
            user_id=user.id,
            action='booking_cancelled',
            entity_type='booking',
            entity_id=booking.id,
            description=f'Booking {booking.booking_reference} cancelled',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success(
            data={
                'booking': {
                    'id': booking.id,
                    'bookingReference': booking.booking_reference,
                    'status': booking.status.value,
                    'refundAmount': float(refund_amount)
                }
            },
            message='Booking cancelled successfully'
        )
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Cancel booking error: {str(e)}")
        return APIResponse.error('An error occurred while cancelling the booking')


@client_bp.route('/trips', methods=['GET'])
@jwt_required()
def get_trips():
    """
    Get user's package tour bookings (trips)
    
    Query Parameters:
        status: Filter by status (active, past, all)
        page: Page number (default: 1)
        perPage: Items per page (default: 10)
    
    Returns:
        200: List of trips
        401: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Get query parameters
        status_filter = request.args.get('status', 'all').strip().lower()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('perPage', 10))
        
        # Build query for package bookings
        query = Booking.query.filter_by(
            user_id=current_user_id,
            booking_type='package'
        )
        
        # Apply status filter
        if status_filter == 'active':
            query = query.filter(
                and_(
                    Booking.status == BookingStatus.CONFIRMED,
                    Booking.departure_date >= datetime.now(timezone.utc)
                )
            )
        elif status_filter == 'past':
            query = query.filter(
                or_(
                    Booking.status == BookingStatus.COMPLETED,
                    Booking.departure_date < datetime.now(timezone.utc)
                )
            )
        
        # Order by departure date
        query = query.order_by(Booking.departure_date.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        trips_data = []
        for booking in pagination.items:
            trip_dict = booking.to_dict()
            
            # Add package details
            if booking.package_id:
                package = Package.query.get(booking.package_id)
                if package:
                    trip_dict['package'] = {
                        'id': package.id,
                        'name': package.name,
                        'destination': f"{package.destination_city}, {package.destination_country}",
                        'duration': f"{package.duration_days} Days / {package.duration_nights} Nights",
                        'hotelName': package.hotel_name,
                        'hotelRating': package.hotel_rating,
                        'featuredImage': package.featured_image,
                        'highlights': package.highlights,
                        'inclusions': package.inclusions,
                        'itinerary': package.itinerary
                    }
            
            trips_data.append(trip_dict)
        
        return APIResponse.success(
            data={
                'trips': trips_data,
                'pagination': {
                    'page': pagination.page,
                    'perPage': pagination.per_page,
                    'totalPages': pagination.pages,
                    'totalItems': pagination.total
                }
            },
            message='Trips retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Get trips error: {str(e)}")
        return APIResponse.error('An error occurred while fetching trips')


@client_bp.route('/trips/<trip_id>', methods=['GET'])
@jwt_required()
def get_trip_details(trip_id):
    """
    Get detailed trip information
    
    Returns:
        200: Trip details
        401: Unauthorized
        404: Trip not found
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Get trip (package booking)
        trip = Booking.query.filter_by(
            id=trip_id,
            user_id=current_user_id,
            booking_type='package'
        ).first()
        
        if not trip:
            return APIResponse.not_found('Trip not found')
        
        trip_dict = trip.to_dict()
        
        # Add package details
        if trip.package_id:
            package = Package.query.get(trip.package_id)
            if package:
                trip_dict['package'] = {
                    'id': package.id,
                    'name': package.name,
                    'slug': package.slug,
                    'description': package.description,
                    'destination': f"{package.destination_city}, {package.destination_country}",
                    'duration': f"{package.duration_days} Days / {package.duration_nights} Nights",
                    'hotelName': package.hotel_name,
                    'hotelRating': package.hotel_rating,
                    'roomType': package.room_type,
                    'featuredImage': package.featured_image,
                    'galleryImages': package.gallery_images,
                    'highlights': package.highlights,
                    'inclusions': package.inclusions,
                    'exclusions': package.exclusions,
                    'itinerary': package.itinerary
                }
        
        # Add passengers
        passengers = []
        for passenger in trip.passengers:
            passengers.append({
                'firstName': passenger.first_name,
                'lastName': passenger.last_name,
                'passengerType': passenger.passenger_type
            })
        
        trip_dict['passengers'] = passengers
        
        return APIResponse.success(
            data={'trip': trip_dict},
            message='Trip details retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Get trip details error: {str(e)}")
        return APIResponse.error('An error occurred while fetching trip details')


@client_bp.route('/contact', methods=['POST'])
@jwt_required()
def submit_contact_form():
    """
    Submit contact/support message
    
    Request Body:
        {
            "category": "general",
            "subject": "Need help with booking",
            "message": "I need assistance with...",
            "bookingReference": "TGT-ABC123" (optional)
        }
    
    Returns:
        200: Message submitted successfully
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
        is_valid, errors, cleaned_data = DashboardSchemas.validate_contact_form(data)
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Create notification for admin
        try:
            # Find admin users
            admin_users = User.query.filter_by(role=UserRole.ADMIN).all()
            
            for admin in admin_users:
                NotificationService.create_notification(
                    user_id=admin.id,
                    notification_type='support_message',
                    title=f'Support Request: {cleaned_data["subject"]}',
                    message=f'From: {user.get_full_name()} ({user.email})\nCategory: {cleaned_data["category"]}\n\n{cleaned_data["message"][:200]}...'
                )
        except Exception as e:
            current_app.logger.error(f"Failed to create admin notification: {str(e)}")
        
        # Send confirmation email to user
        try:
            EmailService.send_email(
                to=user.email,
                subject='Support Request Received',
                body=f"""
                Hello {user.first_name},
                
                We have received your support request:
                
                Subject: {cleaned_data['subject']}
                Category: {cleaned_data['category']}
                
                Our support team will review your message and get back to you within 24 hours.
                
                Thank you for contacting Thrive Travel!
                """
            )
        except Exception as e:
            current_app.logger.error(f"Failed to send confirmation email: {str(e)}")
        
        # Send notification email to support team
        support_email = current_app.config.get('SUPPORT_EMAIL', 'support@thrivetravel.com')
        try:
            EmailService.send_email(
                to=support_email,
                subject=f'Support Request: {cleaned_data["subject"]}',
                body=f"""
                New support request from {user.get_full_name()} ({user.email})
                
                Category: {cleaned_data['category']}
                Subject: {cleaned_data['subject']}
                Booking Reference: {cleaned_data.get('booking_reference', 'N/A')}
                
                Message:
                {cleaned_data['message']}
                
                User ID: {user.id}
                """
            )
        except Exception as e:
            current_app.logger.error(f"Failed to send support email: {str(e)}")
        
        # Log contact form submission
        AuditLogger.log_action(
            user_id=user.id,
            action='contact_form_submitted',
            entity_type='support',
            entity_id=user.id,
            description=f'Contact form submitted: {cleaned_data["subject"]}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success(
            message='Your message has been sent successfully. We will get back to you within 24 hours.'
        )
        
    except Exception as e:
        current_app.logger.error(f"Contact form error: {str(e)}")
        return APIResponse.error('An error occurred while submitting your message')


@client_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    """
    Get user notifications
    
    Query Parameters:
        page: Page number (default: 1)
        perPage: Items per page (default: 20)
        unreadOnly: Show only unread notifications (default: false)
    
    Returns:
        200: List of notifications
        401: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('perPage', 20))
        unread_only = request.args.get('unreadOnly', 'false').lower() == 'true'
        
        # Build query
        query = Notification.query.filter_by(user_id=current_user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        # Order by creation date (newest first)
        query = query.order_by(Notification.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        notifications_data = [notification.to_dict() for notification in pagination.items]
        
        return APIResponse.success(
            data={
                'notifications': notifications_data,
                'pagination': {
                    'page': pagination.page,
                    'perPage': pagination.per_page,
                    'totalPages': pagination.pages,
                    'totalItems': pagination.total
                }
            },
            message='Notifications retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Get notifications error: {str(e)}")
        return APIResponse.error('An error occurred while fetching notifications')


@client_bp.route('/notifications/<notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(notification_id):
    """
    Mark notification as read
    
    Returns:
        200: Notification marked as read
        401: Unauthorized
        404: Notification not found
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Get notification
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user_id
        ).first()
        
        if not notification:
            return APIResponse.not_found('Notification not found')
        
        # Mark as read
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return APIResponse.success(
            data={'notification': notification.to_dict()},
            message='Notification marked as read'
        )
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Mark notification read error: {str(e)}")
        return APIResponse.error('An error occurred while updating notification')

