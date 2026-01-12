
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from decimal import Decimal
import stripe

from app.extensions import db
from app.models import User, Booking, Package, Payment
from app.models.enums import BookingStatus, PaymentStatus, SubscriptionTier, UserRole
from app.api.client.schemas import DashboardSchemas
from app.utils.api_response import APIResponse
from app.utils.email import EmailService
from app.utils.audit_logging import AuditLogger
from app.services.notification import NotificationService

from . import client_bp

@client_bp.route('/bookings', methods=['GET'])
@jwt_required()
def get_bookings():
    """
    Get user bookings with filters and pagination
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
