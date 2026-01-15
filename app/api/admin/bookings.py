from flask import request, current_app
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_, and_, func, desc
from datetime import datetime, timedelta, timezone

from app.api.admin import admin_bp
from app.models import (
    Booking, Passenger, Payment
)
from app.models.enums import (
    BookingStatus
)
from app.extensions import db
from app.utils.decorators import admin_required
from app.utils.api_response import APIResponse
from app.utils.audit_logging import AuditLogger
from app.api.admin.schemas import AdminSchemas

# ===== BOOKING MANAGEMENT =====

@admin_bp.route('/bookings', methods=['GET'])
@admin_required()
def get_bookings():
    """
    Get paginated list of bookings with filtering
    
    Query params:
        - page, perPage: Pagination
        - search: Search in booking reference
        - status: Filter by status
        - bookingType: Filter by type
        - startDate, endDate: Date range filter
        - userId: Filter by user
    """
    try:
        args = request.args.to_dict()
        pagination = AdminSchemas.validate_pagination(args)
        
        query = Booking.query
        
        # Search filter
        if 'search' in args and args['search']:
            search_term = f"%{args['search']}%"
            query = query.filter(Booking.booking_reference.ilike(search_term))
        
        # Status filter
        if 'status' in args and args['status']:
            query = query.filter_by(status=BookingStatus(args['status']))
        
        # Booking type filter
        if 'bookingType' in args and args['bookingType']:
            query = query.filter_by(booking_type=args['bookingType'])
        
        # Date range filter
        start_date, end_date = AdminSchemas.validate_date_range(args)
        if start_date:
            query = query.filter(Booking.created_at >= start_date)
        if end_date:
            query = query.filter(Booking.created_at <= end_date)
        
        # User filter
        if 'userId' in args and args['userId']:
            query = query.filter_by(user_id=args['userId'])
        
        # Sort by creation date (newest first)
        query = query.order_by(desc(Booking.created_at))
        
        # Paginate
        paginated = query.paginate(
            page=pagination['page'],
            per_page=pagination['per_page'],
            error_out=False
        )
        
        # Include customer info in response
        bookings_data = []
        for booking in paginated.items:
            booking_dict = booking.to_dict()
            if booking.customer:
                booking_dict['customer'] = {
                    'id': booking.customer.id,
                    'fullName': booking.customer.get_full_name(),
                    'email': booking.customer.email
                }
            bookings_data.append(booking_dict)
        
        return APIResponse.success({
            'bookings': bookings_data,
            'pagination': {
                'page': paginated.page,
                'perPage': paginated.per_page,
                'totalPages': paginated.pages,
                'totalItems': paginated.total
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get bookings error: {str(e)}")
        return APIResponse.error("Failed to fetch bookings")


@admin_bp.route('/bookings/<booking_id>', methods=['GET'])
@admin_required()
def get_booking(booking_id):
    """Get detailed booking information"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return APIResponse.not_found("Booking not found")
        
        # Get passengers
        passengers = Passenger.query.filter_by(booking_id=booking_id).all()
        
        # Get payments
        payments = Payment.query.filter_by(booking_id=booking_id).all()
        
        booking_data = booking.to_dict()
        booking_data.update({
            'customer': booking.customer.to_dict() if booking.customer else None,
            'passengers': [p.to_dict() for p in passengers],
            'payments': [p.to_dict() for p in payments],
            'package': booking.package.to_dict() if booking.package else None,
            'agent': booking.agent.to_dict() if booking.agent else None
        })
        
        return APIResponse.success({'booking': booking_data})
        
    except Exception as e:
        current_app.logger.error(f"Get booking error: {str(e)}")
        return APIResponse.error("Failed to fetch booking details")


@admin_bp.route('/bookings/<booking_id>', methods=['PATCH'])
@admin_required()
def update_booking(booking_id):
    """Update booking details"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return APIResponse.not_found("Booking not found")
        
        data = request.get_json()
        is_valid, errors, cleaned_data = AdminSchemas.validate_booking_update(data)
        
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Update booking fields
        for key, value in cleaned_data.items():
            if key == 'status':
                setattr(booking, key, BookingStatus(value))
                if value == 'confirmed':
                    booking.confirmed_at = datetime.now(timezone.utc)
                elif value == 'cancelled':
                    booking.cancelled_at = datetime.now(timezone.utc)
            else:
                setattr(booking, key, value)
        
        booking.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='booking_updated',
            entity_type='booking',
            entity_id=booking_id,
            description=f'Admin updated booking {booking.booking_reference}',
            changes=cleaned_data,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success({
            'booking': booking.to_dict()
        }, message='Booking updated successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update booking error: {str(e)}")
        return APIResponse.error("Failed to update booking")


@admin_bp.route('/bookings/<booking_id>/cancel', methods=['POST'])
@admin_required()
def cancel_booking(booking_id):
    """Cancel a booking with reason"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return APIResponse.not_found("Booking not found")
        
        data = request.get_json()
        is_valid, errors, cleaned_data = AdminSchemas.validate_booking_cancellation(data)
        
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now(timezone.utc)
        booking.notes = (booking.notes or '') + f"\n\nCancellation reason: {cleaned_data['reason']}"
        
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='booking_cancelled',
            entity_type='booking',
            entity_id=booking_id,
            description=f'Admin cancelled booking {booking.booking_reference}',
            changes=cleaned_data,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success({
            'booking': booking.to_dict()
        }, message='Booking cancelled successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Cancel booking error: {str(e)}")
        return APIResponse.error("Failed to cancel booking")


@admin_bp.route('/bookings/stats', methods=['GET'])
@admin_required()
def get_booking_stats():
    """Get booking statistics"""
    try:
        # Total bookings
        total_bookings = Booking.query.count()
        
        # Bookings by status
        bookings_by_status = db.session.query(
            Booking.status, func.count(Booking.id)
        ).group_by(Booking.status).all()
        
        # Bookings by type
        bookings_by_type = db.session.query(
            Booking.booking_type, func.count(Booking.id)
        ).group_by(Booking.booking_type).all()
        
        # Total revenue
        total_revenue = db.session.query(func.sum(Booking.total_price)).scalar() or 0
        
        # Average booking value
        avg_booking_value = db.session.query(func.avg(Booking.total_price)).scalar() or 0
        
        # Monthly booking trend (last 12 months)
        booking_trend = []
        revenue_trend = []
        now = datetime.now(timezone.utc)
        
        for i in range(11, -1, -1):
            month_date = now - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i == 0:
                month_end = now
            else:
                next_month = month_start + timedelta(days=32)
                month_end = next_month.replace(day=1) - timedelta(seconds=1)
            
            count = Booking.query.filter(
                and_(
                    Booking.created_at >= month_start,
                    Booking.created_at <= month_end
                )
            ).count()
            
            revenue = db.session.query(func.sum(Booking.total_price)).filter(
                and_(
                    Booking.created_at >= month_start,
                    Booking.created_at <= month_end
                )
            ).scalar() or 0
            
            month_label = month_date.strftime('%b %Y')
            booking_trend.append({'month': month_label, 'count': count})
            revenue_trend.append({'month': month_label, 'revenue': float(revenue)})
        
        return APIResponse.success({
            'totalBookings': total_bookings,
            'bookingsByStatus': {status.value: count for status, count in bookings_by_status},
            'bookingsByType': dict(bookings_by_type),
            'totalRevenue': float(total_revenue),
            'avgBookingValue': float(avg_booking_value),
            'bookingTrend': booking_trend,
            'revenueTrend': revenue_trend
        })
        
    except Exception as e:
        current_app.logger.error(f"Get booking stats error: {str(e)}")
        return APIResponse.error("Failed to fetch booking statistics")
