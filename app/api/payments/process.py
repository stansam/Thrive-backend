from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

from app.api.payments import payment_bp as bp
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.user import User
from app.models.enums import BookingStatus, PaymentStatus
from app.services.payment import PaymentService
from app.extensions import db
from app.utils.api_response import APIResponse
from .utils import handle_payment_error, log_audit

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
