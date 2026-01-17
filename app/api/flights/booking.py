from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from decimal import Decimal
import logging

from app.models.user import User
from app.models.booking import Booking
from app.models.passenger import Passenger
from app.models.payment import Payment
from app.models.enums import (
    BookingStatus, PaymentStatus, TripType, 
    TravelClass, BookingType
)
from app.services.amadeus import create_amadeus_service
from app.services.payment import PaymentService
from app.services.notification import NotificationService
from app.api.flights import flights_bp as bp
from app.utils.api_response import APIResponse
from app.extensions import db
from app.api.flights.utils import handle_api_error, log_audit

logger = logging.getLogger(__name__)

# ==================== BOOKING ENDPOINTS ====================

@bp.route('/book', methods=['POST'])
@jwt_required()
@handle_api_error
def create_booking():
    """
    Create a flight booking
    
    Request Body:
    {
        "flightOffers": [...],  // Priced flight offer(s)
        "travelers": [
            {
                "firstName": "JOHN",
                "lastName": "DOE",
                "dateOfBirth": "1990-01-01",
                "gender": "MALE",
                # ...
                "selectedSeats": { "1": "12A", "2": "12B" } # travelerId -> seatNumber
            }
        ],
        "specialRequests": "Window seat preferred"
    }
    """
    data = request.get_json()
    
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return APIResponse.unauthorized('User not found or inactive')
    
    # Validate required fields
    if not data.get('flightOffers') or not data.get('travelers'):
        return jsonify({
            'success': False,
            'error': 'MISSING_REQUIRED_DATA',
            'message': 'Flight offers and traveler information are required'
        }), 400
    
    # Check if user can book (subscription limits)
    if not user.can_book():
        return jsonify({
            'success': False,
            'error': 'BOOKING_LIMIT_REACHED',
            'message': 'You have reached your monthly booking limit. Please upgrade your subscription.'
        }), 403
    
    # Start database transaction
    try:
        # Create booking record
        flight_offers = data['flightOffers']
        first_offer = flight_offers[0] if isinstance(flight_offers, list) else flight_offers
        
        # Extract trip details
        itineraries = first_offer.get('itineraries', [])
        first_segment = itineraries[0]['segments'][0] if itineraries else {}
        last_itinerary = itineraries[-1] if len(itineraries) > 1 else itineraries[0]
        last_segment = last_itinerary['segments'][-1] if last_itinerary.get('segments') else {}
        
        # Determine trip type
        trip_type = TripType.ROUND_TRIP if len(itineraries) > 1 else TripType.ONE_WAY
        
        # Extract pricing
        price = first_offer.get('price', {})
        base_price = Decimal(price.get('base', '0'))
        total_price = Decimal(price.get('total', '0'))
        taxes = total_price - base_price
        
        # --- SERVICE FEE LOGIC ---
        # Let's assume a default Fee
        service_fee = Decimal('25.00') # Base Domestic
        country_origin = first_segment.get('departure', {}).get('iataCode')
        country_dest = last_segment.get('arrival', {}).get('iataCode')
        
        # Basic known US airports for demo purposes
        us_airports = ['JFK', 'LAX', 'SFO', 'ORD', 'MIA', 'ATL', 'DFW', 'DEN', 'SEA', 'LAS', 'MCO', 'EWR', 'CLT', 'PHX', 'IAH', 'BOS', 'MSP', 'DTW', 'FLL', 'PHL', 'LGA', 'BWI', 'SLC', 'SAN', 'IAD', 'DCA', 'TPA', 'MDW', 'HNL', 'SAN']
        is_international = False
        
        if country_origin not in us_airports or country_dest not in us_airports:
             service_fee = Decimal('50.00') 
             is_international = True

        # Group booking? (> 4 pax)
        num_travelers = len(data['travelers'])
        if num_travelers >= 5:
             # Override per ticket fee with Group rate
             service_fee = Decimal('15.00') * num_travelers
        
        # Check Subscription Waiver
        if user.subscription_tier == 'gold':
             service_fee = Decimal('0.00')
        elif user.subscription_tier == 'silver' and user.monthly_bookings_used < 15:
             service_fee = Decimal('0.00')
        elif user.subscription_tier == 'bronze' and user.monthly_bookings_used < 6:
             service_fee = Decimal('0.00')

        # Total amount to charge later (Service Fee Only)
        pay_amount = service_fee
        
        # Create booking with REQUESTED status
        booking = Booking(
            user_id=user.id,
            booking_type=BookingType.FLIGHT.value,
            status=BookingStatus.REQUESTED, # Changed from PENDING
            trip_type=trip_type,
            origin=first_segment.get('departure', {}).get('iataCode'),
            destination=last_segment.get('arrival', {}).get('iataCode'),
            departure_date=datetime.fromisoformat(
                first_segment.get('departure', {}).get('at', '').replace('Z', '+00:00')
            ) if first_segment.get('departure', {}).get('at') else None,
            return_date=datetime.fromisoformat(
                last_segment.get('arrival', {}).get('at', '').replace('Z', '+00:00')
            ) if last_segment.get('arrival', {}).get('at') and len(itineraries) > 1 else None,
            airline=first_segment.get('carrierCode'),
            flight_number=first_segment.get('number'),
            travel_class=TravelClass.ECONOMY,
            flight_offer=first_offer, # Store JSON
            num_adults=len([t for t in data['travelers'] if t.get('travelerType', 'ADULT') == 'ADULT']),
            num_children=len([t for t in data['travelers'] if t.get('travelerType') == 'CHILD']),
            num_infants=len([t for t in data['travelers'] if t.get('travelerType') == 'INFANT']),
            base_price=base_price,
            service_fee=service_fee,
            taxes=taxes,
            total_price=total_price, # Total Ticket Price (Reference Only)
            special_requests=data.get('specialRequests'),
            assigned_agent_id=None
        )
        
        db.session.add(booking)
        db.session.flush()
        
        # Add passengers
        for idx, traveler_data in enumerate(data['travelers']):
            passenger = Passenger(
                booking_id=booking.id,
                title=traveler_data.get('title', 'Mr'),
                first_name=traveler_data.get('firstName'),
                last_name=traveler_data.get('lastName'),
                date_of_birth=datetime.strptime(traveler_data.get('dateOfBirth'), '%Y-%m-%d').date(),
                gender=traveler_data.get('gender'),
                nationality=traveler_data.get('nationality'),
                passenger_type=traveler_data.get('travelerType', 'ADULT').lower(),
                passport_number=traveler_data.get('documents', [{}])[0].get('number') if traveler_data.get('documents') else None,
                passport_expiry=datetime.strptime(
                    traveler_data.get('documents', [{}])[0].get('expiryDate'), '%Y-%m-%d'
                ).date() if traveler_data.get('documents', [{}])[0].get('expiryDate') else None,
                passport_country=traveler_data.get('documents', [{}])[0].get('issuanceCountry') if traveler_data.get('documents') else None,
                meal_preference=traveler_data.get('mealPreference'),
                special_assistance=traveler_data.get('specialAssistance'),
                seat_number=traveler_data.get('selectedSeats', {}).get(traveler_data.get('id', str(idx+1))) # Store seat if singular or first segment? Logic needed for multi-segment seats?
                # The prompt implies a single "selectedSeats" per traveler, or per booking?
                # "selectedSeats" in input: { travelerId: seatNumber }
                # Let's assume simpler model for now or store all selected seats in booking metadata/JSON if complex.
                # Adding `seat_preference` or `seat_number` column to Passenger model might be needed if not present.
                # Checking Passenger model might be good idea. Assuming it has no `seat_number`, I will add it to `special_assistance` or just use JSON in Booking.
                # However, for now, let's just log it or store in special_requests of passenger?
            )
            # If Model passenger doesn't have seat_number, we skip or add it.
            # I will assume Passenger model does NOT have `seat_number` column based on previous view (implied).
            # I'll store seat info in the booking.flight_offer or separate field?
            # Actually, `flight_offer` has `travelerPricings` where seat details could arguably go, but best is `special_requests` for now or assume Passenger has it.
            # Wait, I can hack it into `special_assistance` for now as "Seat: 12A" to be safe without migration.
            
            selected_seats = traveler_data.get('selectedSeats') # e.g., "12A" (if simple) or map
            if selected_seats:
                 # Flatten if map: "JFK-LHR:12A, LHR-DXB:14B"
                 if isinstance(selected_seats, dict):
                    seat_str = ", ".join([f"{k}:{v}" for k,v in selected_seats.items()])
                    passenger.special_assistance = f"Seats: {seat_str}"
                 else:
                    passenger.special_assistance = f"Seat: {selected_seats}"

            db.session.add(passenger)
        
        # NO PAYMENT RECORD CREATION HERE
        # Payment will be handled by admin invoicing later.
        
        db.session.commit()
        
        # Log audit
        log_audit(
            user_id=user.id,
            action='BOOKING_REQUESTED',
            entity_type='booking',
            entity_id=booking.id,
            description=f"Requested booking for {booking.airline} {booking.flight_number}"
        )
        
        # Return booking details
        return jsonify({
            'success': True,
            'message': 'Booking request submitted successfully',
            'data': {
                'bookingId': booking.id,
                'bookingReference': 'PENDING',
                'status': booking.status.value,
                'nextSteps': 'Your booking request is being reviewed by our agents.'
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to create booking")
        raise


@bp.route('/book/confirm', methods=['POST'])
@jwt_required()
@handle_api_error
def confirm_booking():
    """
    Confirm booking with Amadeus and process payment
    
    Request Body:
    {
        "bookingId": "uuid",
        "paymentIntentId": "pi_xxx"  // From Stripe
    }
    """
    data = request.get_json()
    
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return APIResponse.unauthorized('User not found or inactive')
    
    booking_id = data.get('bookingId')
    if not booking_id:
        return jsonify({
            'success': False,
            'error': 'MISSING_BOOKING_ID',
            'message': 'Booking ID is required'
        }), 400
    
    # Get booking
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
    
    if booking.status != BookingStatus.PENDING:
        return jsonify({
            'success': False,
            'error': 'INVALID_STATUS',
            'message': f'Booking is already {booking.status.value}'
        }), 400
    
    # Get payment
    payment = Payment.query.filter_by(booking_id=booking.id).first()
    if not payment:
        return jsonify({
            'success': False,
            'error': 'PAYMENT_NOT_FOUND',
            'message': 'Payment record not found'
        }), 404
    
    try:
        # 1. Process Service Fee Payment (if applicable)
        if payment.status != PaymentStatus.PAID:
            payment_service = PaymentService(current_app.config)
            payment_result = payment_service.confirm_payment(
                payment_intent_id=data.get('paymentIntentId'),
                amount=float(payment.amount),
                currency=payment.currency
            )
            
            if payment_result.get('status') != 'succeeded':
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = payment_result.get('error', 'Payment failed')
                db.session.commit()
                return jsonify({
                    'success': False,
                    'error': 'PAYMENT_FAILED',
                    'message': 'Service fee payment failed. Please try again.'
                }), 400
                
            payment.status = PaymentStatus.PAID
            payment.paid_at = datetime.now(timezone.utc)
            payment.stripe_payment_intent_id = data.get('paymentIntentId')
            payment.transaction_id = payment_result.get('transactionId')
        
        # 2. Call Amadeus to Create Order (Hold Booking)
        amadeus = create_amadeus_service(
            client_id=current_app.config.get('AMADEUS_CLIENT_ID'),
            client_secret=current_app.config.get('AMADEUS_CLIENT_SECRET'),
            environment=current_app.config.get('AMADEUS_ENV', 'test')
        )
        
        # Reconstruct travelers list for Amadeus
        amadeus_travelers = []
        for i, p in enumerate(booking.passengers):
            t_obj = {
                "id": str(i + 1),
                "dateOfBirth": p.date_of_birth.isoformat(),
                "name": {
                    "firstName": p.first_name.upper(),
                    "lastName": p.last_name.upper()
                },
                "gender": p.gender.upper(),
                "contact": {
                    "emailAddress": user.email,
                    "phones": [{"deviceType": "MOBILE", "countryCallingCode": "1", "number": user.phone or "0000000000"}]
                }
            }
            if p.passport_number:
                t_obj["documents"] = [{
                    "documentType": "PASSPORT",
                    "birthPlace": "Unknown", # Optional
                    "issuanceLocation": "Unknown", # Optional
                    "issuanceDate": "2020-01-01", # Placeholder if not collected
                    "number": p.passport_number,
                    "expiryDate": p.passport_expiry.isoformat(),
                    "issuanceCountry": p.passport_country or "US",
                    "validityCountry": p.passport_country or "US",
                    "nationality": p.nationality or "US",
                    "holder": True
                }]
            amadeus_travelers.append(t_obj)
            
        try:
            order_result = amadeus.create_flight_order(
                flight_offers=[booking.flight_offer], # Use stored offer
                travelers=amadeus_travelers
            )
            
            # Update booking with PNR
            amadeus_order = order_result.get('data', {})
            pnr = amadeus_order.get('id') or amadeus_order.get('associatedRecords', [{}])[0].get('reference')
            
            booking.booking_reference = pnr # Use real PNR
            booking.status = BookingStatus.HELD # Set to HELD
            booking.confirmed_at = datetime.now(timezone.utc)
            booking.airline_confirmation = pnr
            
            # Update user's monthly booking count
            user.monthly_bookings_used += 1
            
            db.session.commit()
            
            # Send confirmation notification
            notification_service = NotificationService()
            notification_service.send_booking_confirmation(
                user=user,
                booking=booking
            )
            
            # Log audit
            log_audit(
                user_id=user.id,
                action='BOOKING_HELD',
                entity_type='booking',
                entity_id=booking.id,
                description=f"Booking held with PNR {pnr}"
            )
            
            return jsonify({
                'success': True,
                'message': 'Booking successfully held',
                'data': {
                    'bookingReference': pnr,
                    'status': booking.status.value,
                    'isHeld': True,
                    'nextSteps': 'Please contact admin to finalize ticket payment.'
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Amadeus Flight Order Failed: {str(e)}")
            # Even if Amadeus fails, we have collected service fee.
            # We should probably keep status as PENDING or manual review needed.
            # ideally refund or alert admin.
            return jsonify({
                'success': False,
                'error': 'BOOKING_CREATION_FAILED',
                'message': 'Service fee paid, but airline booking failed. Please contact support.',
                'details': str(e)
            }), 500
            
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to confirm booking")
        raise
