from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.payments import payment_bp as bp
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.user import User
from app.utils.api_response import APIResponse
from .utils import handle_payment_error

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
