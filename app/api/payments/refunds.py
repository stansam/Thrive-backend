from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

from app.api.payments import payment_bp as bp
from app.models.payment import Payment
from app.models.user import User
from app.models.enums import BookingStatus, PaymentStatus
from app.services.payment import PaymentService
from app.extensions import db
from app.utils.api_response import APIResponse
from .utils import handle_payment_error, log_audit

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
