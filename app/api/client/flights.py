
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_, or_
from datetime import datetime, timezone

from app.models import User, Booking
from app.models.enums import BookingStatus, BookingType
from app.utils.api_response import APIResponse

from . import client_bp

@client_bp.route('/flights', methods=['GET'])
@jwt_required()
def get_flights():
    """
    Get user flight bookings and stats
    
    Returns:
        200: Flight summary stats and list of flight bookings
        401: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Stats
        upcoming_count = Booking.query.filter(
            and_(
                Booking.user_id == current_user_id,
                Booking.booking_type == BookingType.FLIGHT,
                Booking.departure_date >= datetime.now(timezone.utc),
                Booking.status.in_([BookingStatus.CONFIRMED])
            )
        ).count()
        
        pending_quote_count = Booking.query.filter(
            and_(
                Booking.user_id == current_user_id,
                Booking.booking_type == BookingType.FLIGHT,
                Booking.status == BookingStatus.PENDING
            )
        ).count()
        
        ticketed_count = Booking.query.filter(
            and_(
                Booking.user_id == current_user_id,
                Booking.booking_type == BookingType.FLIGHT,
                Booking.status == BookingStatus.CONFIRMED
            )
        ).count()
        
        cancelled_count = Booking.query.filter(
            and_(
                Booking.user_id == current_user_id,
                Booking.booking_type == BookingType.FLIGHT,
                Booking.status == BookingStatus.CANCELLED
            )
        ).count()
        
        # Flight List
        # Supports filters: status, search query param handled optionally or by general bookings
        status_filter = request.args.get('status', 'all').lower()
        
        query = Booking.query.filter(
            Booking.user_id == current_user_id,
            Booking.booking_type == BookingType.FLIGHT
        )
        
        if status_filter != 'all' and status_filter:
             # Map convenient front-end statuses if needed, or use exact enum
             if status_filter in BookingStatus.__members__.values():
                 query = query.filter(Booking.status == status_filter)
        
        query = query.order_by(Booking.departure_date.desc())
        
        # Limit for initial view or paginate
        flights = query.limit(50).all()
        
        flight_list = []
        for flight in flights:
            f_dict = flight.to_dict()
            # Enrich with airline name, logo, route if stored in metadata or distinct fields
            # Assuming basic details are in Booking model or related metadata
            # For now, using standard to_dict response
            flight_list.append(f_dict)

        return APIResponse.success(
            data={
                'summary': {
                    'upcoming': upcoming_count,
                    'pending_quote': pending_quote_count,
                    'ticketed': ticketed_count,
                    'cancelled': cancelled_count
                },
                'flights': flight_list
            },
            message="Flights retrieved successfully"
        )

    except Exception as e:
        current_app.logger.error(f"Get flights error: {str(e)}")
        return APIResponse.error('An error occurred while fetching flights')
