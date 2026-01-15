
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import stripe

from app.extensions import db
from app.models import User, Payment
from app.models.enums import PaymentStatus, SubscriptionTier
from app.api.client.schemas import DashboardSchemas
from app.utils.api_response import APIResponse
from app.utils.email import EmailService
from app.utils.audit_logging import AuditLogger
from app.services.notification import NotificationService

from app.api.client import client_bp

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
                # Note: You'll need to add stripe_customer_id field to User model or custom logic if not present
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
