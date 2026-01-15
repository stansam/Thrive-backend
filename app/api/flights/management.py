from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
import logging

from app.models.user import User
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.enums import BookingStatus, PaymentStatus
from app.services.payment import PaymentService
from app.services.notification import NotificationService
from app.api.flights import flights_bp as bp
from app.utils.api_response import APIResponse
from app.extensions import db
from app.api.flights.utils import handle_api_error, log_audit

logger = logging.getLogger(__name__)

# ==================== BOOKING MANAGEMENT ====================

@bp.route('/bookings', methods=['GET'])
@jwt_required()
@handle_api_error
def get_user_bookings():
    """Get all bookings for current user"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return APIResponse.unauthorized('User not found or inactive')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    
    query = Booking.query.filter_by(user_id=user.id)
    
    if status:
        try:
            query = query.filter_by(status=BookingStatus(status))
        except ValueError:
            pass
    
    query = query.order_by(Booking.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    bookings = [{
        'id': b.id,
        'bookingReference': b.booking_reference,
        'status': b.status.value,
        'origin': b.origin,
        'destination': b.destination,
        'departureDate': b.departure_date.isoformat() if b.departure_date else None,
        'returnDate': b.return_date.isoformat() if b.return_date else None,
        'totalPrice': float(b.total_price),
        'passengers': b.get_total_passengers(),
        'createdAt': b.created_at.isoformat()
    } for b in pagination.items]
    
    return jsonify({
        'success': True,
        'data': bookings,
        'pagination': {
            'page': page,
            'perPage': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@bp.route('/bookings/<booking_id>', methods=['GET'])
@jwt_required()
@handle_api_error
def get_booking_details(booking_id):
    """Get detailed booking information"""
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
    
    passengers = [{
        'id': p.id,
        'firstName': p.first_name,
        'lastName': p.last_name,
        'dateOfBirth': p.date_of_birth.isoformat() if p.date_of_birth else None,
        'passengerType': p.passenger_type,
        'ticketNumber': p.ticket_number,
        'seatNumber': p.seat_number
    } for p in booking.passengers]
    
    payments = [{
        'id': p.id,
        'amount': float(p.amount),
        'currency': p.currency,
        'status': p.status.value,
        'paymentMethod': p.payment_method,
        'paidAt': p.paid_at.isoformat() if p.paid_at else None
    } for p in booking.payments]
    
    return jsonify({
        'success': True,
        'data': {
            'id': booking.id,
            'bookingReference': booking.booking_reference,
            'status': booking.status.value,
            'tripType': booking.trip_type.value if booking.trip_type else None,
            'origin': booking.origin,
            'destination': booking.destination,
            'departureDate': booking.departure_date.isoformat() if booking.departure_date else None,
            'returnDate': booking.return_date.isoformat() if booking.return_date else None,
            'airline': booking.airline,
            'flightNumber': booking.flight_number,
            'travelClass': booking.travel_class.value if booking.travel_class else None,
            'basePrice': float(booking.base_price),
            'serviceFee': float(booking.service_fee),
            'taxes': float(booking.taxes),
            'totalPrice': float(booking.total_price),
            'specialRequests': booking.special_requests,
            'airlineConfirmation': booking.airline_confirmation,
            'passengers': passengers,
            'payments': payments,
            'createdAt': booking.created_at.isoformat(),
            'confirmedAt': booking.confirmed_at.isoformat() if booking.confirmed_at else None
        }
    }), 200


@bp.route('/bookings/<booking_id>/cancel', methods=['POST'])
@jwt_required()
@handle_api_error
def cancel_booking(booking_id):
    """Cancel a booking"""
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
    
    if booking.status == BookingStatus.CANCELLED:
        return jsonify({
            'success': False,
            'error': 'ALREADY_CANCELLED',
            'message': 'Booking is already cancelled'
        }), 400
    
    if booking.status == BookingStatus.COMPLETED:
        return jsonify({
            'success': False,
            'error': 'CANNOT_CANCEL',
            'message': 'Cannot cancel completed bookings'
        }), 400
    
    try:
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now(timezone.utc)
        
        # Process refund if payment was made
        payment = Payment.query.filter_by(
            booking_id=booking.id,
            status=PaymentStatus.PAID
        ).first()
        
        if payment:
            payment_service = PaymentService(current_app.config)
            refund_result = payment_service.process_refund(
                payment_intent_id=payment.stripe_payment_intent_id,
                amount=float(payment.amount),
                reason='Customer requested cancellation'
            )
            
            if refund_result.get('status') == 'succeeded':
                payment.status = PaymentStatus.REFUNDED
                payment.refunded_at = datetime.now(timezone.utc)
                payment.refund_amount = payment.amount
        
        db.session.commit()
        
        # Send cancellation notification
        notification_service = NotificationService()
        notification_service.send_cancellation_notification(
            user=user,
            booking=booking
        )
        
        # Log audit
        log_audit(
            user_id=user.id,
            action='BOOKING_CANCELLED',
            entity_type='booking',
            entity_id=booking.id,
            description=f"Cancelled booking {booking.booking_reference}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Booking cancelled successfully',
            'data': {
                'bookingReference': booking.booking_reference,
                'status': booking.status.value,
                'refundStatus': payment.status.value if payment else None
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'INTERNAL_SERVER_ERROR',
            'message': str(e)
        }), 500
