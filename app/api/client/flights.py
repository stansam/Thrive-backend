
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_, or_
from datetime import datetime, timezone

from app.models import User, Booking
from app.models.enums import BookingStatus, BookingType
from app.utils.api_response import APIResponse

from app.api.client import client_bp

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
                Booking.status == BookingStatus.PENDING or Booking.status == BookingStatus.REQUESTED
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
            f_dict = flight.to_dict(include_relations=False)
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

@client_bp.route('/flights/<booking_reference>', methods=['GET'])
@jwt_required()
def get_flight_details(booking_reference):
    """
    Get detailed flight booking info for the Concierge Page
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
            
        booking = Booking.query.filter_by(
            booking_reference=booking_reference,
            user_id=current_user_id
        ).first()
        
        if not booking:
            return APIResponse.not_found('Booking not found')
            
        # --- Construct Spec Response ---
        
        # 1. Status Mapping
        # Mapping internal status to UI Label logic
        bs = booking.status
        ui_status_label = "Processing"
        
        # Simple mapper based on spec
        if bs == BookingStatus.REQUESTED:
            ui_status_label = "Quote Requested"
        elif bs == BookingStatus.PENDING: # Pending internal check
            ui_status_label = "Quote Prepared" 
        elif bs == BookingStatus.CONFIRMED:
            ui_status_label = "Booking Confirmed"
        elif bs == BookingStatus.CANCELLED:
            ui_status_label = "Cancelled"
            
        # Logic for "Awaiting Service Fee" vs "Awaiting Airline Payment"
        # We need to check Payments
        service_fee_paid = False
        airline_fare_paid = False
        
        # Iterate payments to check what is covered
        # Ideally Payment model has metadata or type.
        # For now, we assume if Total Paid >= Service Fee, service fee is paid?
        # Or if there is ANY payment.
        
        total_paid = sum([p.amount for p in booking.payments if p.status.name == 'PAID'])
        
        if total_paid >= booking.service_fee and booking.service_fee > 0:
            service_fee_paid = True
            
        # If total paid covers total price?
        if total_paid >= booking.total_price:
            airline_fare_paid = True
            
        # Refine status based on payment
        if bs == BookingStatus.PENDING and not service_fee_paid and booking.service_fee > 0:
             ui_status_label = "Awaiting Service Fee"
        elif bs == BookingStatus.PENDING and service_fee_paid:
             ui_status_label = "Processing Tickets" # or "Quote Accepted" / "Service Fee Paid"
        elif bs == BookingStatus.CONFIRMED and not airline_fare_paid:
             ui_status_label = "Awaiting Airline Payment"
        elif bs == BookingStatus.CONFIRMED and airline_fare_paid:
             ui_status_label = "Tickets Issued" # If ticket numbers exist
             if not booking.ticket_numbers:
                 ui_status_label = "Ticketing in Progress"

        # 2. Flight Details
        flight_details = {
            "airline_name": booking.airline or "TBD",
            "airline_code": "XX", # Placeholder or extract from flight_offer
            "flight_numbers": [booking.flight_number] if booking.flight_number else [],
            "origin": booking.origin,
            "destination": booking.destination,
            "departure_date": booking.departure_date.isoformat() if booking.departure_date else None,
            "return_date": booking.return_date.isoformat() if booking.return_date else None,
            "cabin_class": booking.travel_class.value if booking.travel_class else "Economy"
        }

        # 3. Passengers
        passengers_data = []
        for p in booking.passengers:
            passengers_data.append({
                "full_name": f"{p.first_name} {p.last_name}",
                "passenger_type": p.passenger_type.upper() if p.passenger_type else "ADT" 
            })

        # 4. Pricing (Split View)
        pricing_data = {
            "service_fee": {
                "amount": float(booking.service_fee),
                "currency": "USD",
                "status": "PAID" if service_fee_paid else "UNPAID",
                "invoice_url":  f"/api/documents/invoice/{booking.id}/service" if service_fee_paid else None, # Mock URL
                "payment_link": f"/bookings/{booking.booking_reference}/pay/service" if not service_fee_paid else None
            },
            "airline_fare": {
                "amount": float(booking.base_price + booking.taxes - booking.discount),
                "currency": "USD",
                "status": "PAID" if airline_fare_paid else "UNPAID",
                 "invoice_url":  f"/api/documents/invoice/{booking.id}/airline" if airline_fare_paid else None,
                "payment_link": f"/bookings/{booking.booking_reference}/pay/airline" if not airline_fare_paid else None
            }
        }
        
        # 5. Documents
        # Mocking documents for now based on status, or retrieving if there's a Document model (using placeholders/logic)
        documents = []
        if service_fee_paid:
            documents.append({
                "id": "doc_sf_inv",
                "type": "SERVICE_INVOICE",
                "filename": f"Service_Fee_{booking.booking_reference}.pdf",
                "version": 1,
                "uploaded_at": booking.created_at.isoformat(), # approximation
                "download_url": "#"
            })
        if airline_fare_paid:
             documents.append({
                "id": "doc_air_inv",
                "type": "AIRLINE_INVOICE",
                "filename": f"Flight_Invoice_{booking.booking_reference}.pdf",
                "version": 1,
                "uploaded_at": booking.confirmed_at.isoformat() if booking.confirmed_at else datetime.now(timezone.utc).isoformat(),
                "download_url": "#"
            })
        if booking.ticket_numbers:
             documents.append({
                "id": "doc_tkt",
                "type": "TICKET",
                "filename": f"ETicket_{booking.booking_reference}.pdf",
                "version": 1,
                "uploaded_at": booking.confirmed_at.isoformat() if booking.confirmed_at else datetime.now(timezone.utc).isoformat(),
                "download_url": "#"
            })

        # 6. Activity Log (Notifications)
        from app.models.notification import Notification
        notifications = Notification.query.filter_by(booking_id=booking.id).order_by(Notification.created_at.desc()).all()
        activity_log = [{
            "message": n.title, # Using title as primary message
            "created_at": n.created_at.isoformat()
        } for n in notifications]

        response_data = {
            "booking_reference": booking.booking_reference,
            "status": ui_status_label,
            "created_at": booking.created_at.isoformat(),
            "updated_at": booking.updated_at.isoformat() if booking.updated_at else None,
            "flight_details": flight_details,
            "passengers": passengers_data,
            "pricing": pricing_data,
            "documents": documents,
            "activity_log": activity_log
        }

        return APIResponse.success(data=response_data)

    except Exception as e:
        current_app.logger.error(f"Get detailed flight error: {str(e)}")
        return APIResponse.error('An error occurred while fetching flight details')
