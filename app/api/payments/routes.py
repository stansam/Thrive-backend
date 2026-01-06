"""
Payment API Routes
Provides endpoints for payment processing and management
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
import logging
from functools import wraps
from app.utils.api_response import APIResponse
from app.extensions import db
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.enums import BookingStatus, PaymentStatus
from app.services.payment import PaymentService, PaymentServiceError
from app.api.payments import payment_bp as bp
logger = logging.getLogger(__name__)

def handle_payment_error(f):
    """Decorator for consistent payment error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except PaymentServiceError as e:
            logger.error(f"Payment service error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'PAYMENT_ERROR',
                'message': str(e)
            }), 400
        except Exception as e:
            logger.exception("Unexpected error in payment endpoint")
            return jsonify({
                'success': False,
                'error': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred. Please try again.'
            }), 500
    return decorated_function


def log_audit(user_id, action, entity_type, entity_id, description):
    """Helper to log audit entries"""
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {str(e)}")


# ==================== PAYMENT INTENT ENDPOINTS ====================

@bp.route('/create-intent', methods=['POST'])
@jwt_required()
@handle_payment_error
def create_payment_intent():
    """
    Create a Stripe payment intent
    
    Request Body:
    {
        "bookingId": "uuid",
        "amount": 1000.00,
        "currency": "USD"
    }
    """
    data = request.get_json()
    
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return APIResponse.unauthorized('User not found or inactive')
    
    # Validate required fields
    booking_id = data.get('bookingId')
    amount = data.get('amount')
    currency = data.get('currency', 'USD')
    
    if not booking_id or not amount:
        return jsonify({
            'success': False,
            'error': 'MISSING_FIELDS',
            'message': 'Booking ID and amount are required'
        }), 400
    
    # Verify booking belongs to user
    booking = Booking.query.filter_by(
        id=booking_id,
        user_id=user.id
    ).first()
    
    if not booking:
        return jsonify({
            'success': False,
            'error': 'BOOKING_NOT_FOUND',
            'message': 'Booking not found'
        }), 404
    
    # Verify amount matches booking
    if float(amount) != float(booking.total_price):
        return jsonify({
            'success': False,
            'error': 'AMOUNT_MISMATCH',
            'message': 'Payment amount does not match booking total'
        }), 400
    
    # Create payment intent
    payment_service = PaymentService(current_app.config)
    
    result = payment_service.create_payment_intent(
        amount=float(amount),
        currency=currency.lower(),
        customer_email=user.email,
        metadata={
            'booking_id': booking_id,
            'booking_reference': booking.booking_reference,
            'user_id': user.id
        }
    )
    
    if result.get('success'):
        # Update payment record with intent ID
        payment = Payment.query.filter_by(booking_id=booking_id).first()
        if payment:
            payment.stripe_payment_intent_id = result['paymentIntentId']
            db.session.commit()
        
        # Log audit
        log_audit(
            user_id=user.id,
            action='PAYMENT_INTENT_CREATED',
            entity_type='payment',
            entity_id=payment.id if payment else None,
            description=f"Created payment intent for booking {booking.booking_reference}"
        )
        
        return jsonify({
            'success': True,
            'clientSecret': result['clientSecret'],
            'paymentIntentId': result['paymentIntentId']
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'INTENT_CREATION_FAILED',
            'message': 'Failed to create payment intent'
        }), 500


@bp.route('/confirm', methods=['POST'])
@jwt_required()
@handle_payment_error
def confirm_payment():
    """
    Confirm a payment (called after successful Stripe payment)
    
    Request Body:
    {
        "paymentIntentId": "pi_xxx",
        "bookingId": "uuid"
    }
    """
    data = request.get_json()
    
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return APIResponse.unauthorized('User not found or inactive')
    
    payment_intent_id = data.get('paymentIntentId')
    booking_id = data.get('bookingId')
    
    if not payment_intent_id or not booking_id:
        return jsonify({
            'success': False,
            'error': 'MISSING_FIELDS',
            'message': 'Payment intent ID and booking ID are required'
        }), 400
    
    # Get booking and payment
    booking = Booking.query.filter_by(
        id=booking_id,
        user_id=user.id
    ).first()
    
    if not booking:
        return jsonify({
            'success': False,
            'error': 'BOOKING_NOT_FOUND',
            'message': 'Booking not found'
        }), 404
    
    payment = Payment.query.filter_by(
        booking_id=booking_id,
        stripe_payment_intent_id=payment_intent_id
    ).first()
    
    if not payment:
        return jsonify({
            'success': False,
            'error': 'PAYMENT_NOT_FOUND',
            'message': 'Payment record not found'
        }), 404
    
    # Confirm payment with Stripe
    payment_service = PaymentService(current_app.config)
    
    result = payment_service.confirm_payment(
        payment_intent_id=payment_intent_id,
        amount=float(payment.amount),
        currency=payment.currency
    )
    
    if result.get('success') and result.get('status') == 'succeeded':
        # Update payment status
        payment.status = PaymentStatus.PAID
        payment.paid_at = datetime.now(timezone.utc)
        payment.transaction_id = result.get('transactionId')
        
        # Update booking status
        booking.status = BookingStatus.CONFIRMED
        booking.confirmed_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Log audit
        log_audit(
            user_id=user.id,
            action='PAYMENT_CONFIRMED',
            entity_type='payment',
            entity_id=payment.id,
            description=f"Payment confirmed for booking {booking.booking_reference}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Payment confirmed successfully',
            'data': {
                'paymentId': payment.id,
                'bookingReference': booking.booking_reference,
                'status': payment.status.value
            }
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'PAYMENT_NOT_CONFIRMED',
            'message': result.get('message', 'Payment could not be confirmed')
        }), 400


# ==================== REFUND ENDPOINTS ====================

@bp.route('/refund', methods=['POST'])
@jwt_required()
@handle_payment_error
def process_refund():
    """
    Process a refund for a payment
    
    Request Body:
    {
        "paymentId": "uuid",
        "amount": 1000.00,  // Optional, full refund if not provided
        "reason": "Customer requested cancellation"
    }
    """
    data = request.get_json()
    
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return APIResponse.unauthorized('User not found or inactive')
    
    payment_id = data.get('paymentId')
    if not payment_id:
        return jsonify({
            'success': False,
            'error': 'MISSING_PAYMENT_ID',
            'message': 'Payment ID is required'
        }), 400
    
    # Get payment
    payment = Payment.query.filter_by(
        id=payment_id,
        user_id=user.id
    ).first()
    
    if not payment:
        return jsonify({
            'success': False,
            'error': 'PAYMENT_NOT_FOUND',
            'message': 'Payment not found'
        }), 404
    
    if payment.status != PaymentStatus.PAID:
        return jsonify({
            'success': False,
            'error': 'INVALID_STATUS',
            'message': f'Cannot refund payment with status: {payment.status.value}'
        }), 400
    
    # Process refund
    payment_service = PaymentService(current_app.config)
    
    result = payment_service.process_refund(
        payment_intent_id=payment.stripe_payment_intent_id,
        amount=data.get('amount'),
        reason=data.get('reason')
    )
    
    if result.get('success'):
        # Update payment status
        payment.status = PaymentStatus.REFUNDED
        payment.refunded_at = datetime.now(timezone.utc)
        payment.refund_amount = result.get('amount')
        payment.refund_reason = data.get('reason')
        
        # Update booking status
        booking = payment.booking
        if booking:
            booking.status = BookingStatus.CANCELLED
            booking.cancelled_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Log audit
        log_audit(
            user_id=user.id,
            action='PAYMENT_REFUNDED',
            entity_type='payment',
            entity_id=payment.id,
            description=f"Refunded payment for booking {booking.booking_reference if booking else 'N/A'}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Refund processed successfully',
            'data': {
                'refundId': result.get('refundId'),
                'amount': result.get('amount'),
                'currency': result.get('currency')
            }
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'REFUND_FAILED',
            'message': 'Failed to process refund'
        }), 500


# ==================== PAYMENT STATUS ENDPOINTS ====================

@bp.route('/status/<payment_id>', methods=['GET'])
@jwt_required()
@handle_payment_error
def get_payment_status(payment_id):
    """Get payment status"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return APIResponse.unauthorized('User not found or inactive')
    
    payment = Payment.query.filter_by(
        id=payment_id,
        user_id=user.id
    ).first()
    
    if not payment:
        return jsonify({
            'success': False,
            'error': 'PAYMENT_NOT_FOUND',
            'message': 'Payment not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'id': payment.id,
            'paymentReference': payment.payment_reference,
            'amount': float(payment.amount),
            'currency': payment.currency,
            'status': payment.status.value,
            'paymentMethod': payment.payment_method,
            'createdAt': payment.created_at.isoformat(),
            'paidAt': payment.paid_at.isoformat() if payment.paid_at else None,
            'refundedAt': payment.refunded_at.isoformat() if payment.refunded_at else None
        }
    }), 200


@bp.route('/booking/<booking_id>', methods=['GET'])
@jwt_required()
@handle_payment_error
def get_booking_payments(booking_id):
    """Get all payments for a booking"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return APIResponse.unauthorized('User not found or inactive')
    
    booking = Booking.query.filter_by(
        id=booking_id,
        user_id=user.id
    ).first()
    
    if not booking:
        return jsonify({
            'success': False,
            'error': 'BOOKING_NOT_FOUND',
            'message': 'Booking not found'
        }), 404
    
    payments = Payment.query.filter_by(booking_id=booking_id).all()
    
    payments_data = [{
        'id': p.id,
        'paymentReference': p.payment_reference,
        'amount': float(p.amount),
        'currency': p.currency,
        'status': p.status.value,
        'paymentMethod': p.payment_method,
        'paidAt': p.paid_at.isoformat() if p.paid_at else None
    } for p in payments]
    
    return jsonify({
        'success': True,
        'data': payments_data
    }), 200


# ==================== WEBHOOK ENDPOINT ====================

@bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events
    
    This endpoint receives notifications from Stripe about payment events
    """
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    if not sig_header:
        return jsonify({'error': 'Missing signature'}), 400
    
    try:
        payment_service = PaymentService(current_app.config)
        event_data = payment_service.handle_webhook(payload, sig_header)
        
        event_type = event_data.get('event_type')
        
        # Handle different event types
        if event_type == 'payment_succeeded':
            payment_intent_id = event_data.get('payment_intent_id')
            
            # Find payment and update status
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            
            if payment and payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.PAID
                payment.paid_at = datetime.now(timezone.utc)
                
                # Update booking
                if payment.booking:
                    payment.booking.status = BookingStatus.CONFIRMED
                    payment.booking.confirmed_at = datetime.now(timezone.utc)
                
                db.session.commit()
                
                logger.info(f"Webhook: Payment succeeded for {payment_intent_id}")
        
        elif event_type == 'payment_failed':
            payment_intent_id = event_data.get('payment_intent_id')
            
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            
            if payment:
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = event_data.get('error', 'Payment failed')
                db.session.commit()
                
                logger.warning(f"Webhook: Payment failed for {payment_intent_id}")
        
        elif event_type == 'refund_processed':
            # Handle refund notification
            logger.info(f"Webhook: Refund processed")
        
        return jsonify({'received': True}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 400