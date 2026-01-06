"""
Flight Booking API Routes
Provides endpoints for flight search, pricing, booking, and management
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from decimal import Decimal
import logging
from functools import wraps
from app.utils.api_response import APIResponse
from app.extensions import db
from app.models.user import User
from app.models.booking import Booking
from app.models.passenger import Passenger
from app.models.payment import Payment
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.models.enums import (
    BookingStatus, PaymentStatus, TripType, 
    TravelClass, NotificationType, BookingType
)
from app.services.amadeus import (
    create_amadeus_service, AmadeusAPIError, 
    ValidationError, BookingError, RateLimitError,
    TravelClass as AmadeusTravelClass
)
from app.services.payment import PaymentService
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)
from app.api.flights import flights_bp as bp

# ==================== UTILITY FUNCTIONS ====================

def handle_api_error(f):
    """Decorator for consistent error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error: {e.message}")
            return jsonify({
                'success': False,
                'error': 'VALIDATION_ERROR',
                'message': e.message,
                'details': e.response
            }), 400
        except RateLimitError as e:
            logger.warning("Rate limit exceeded")
            return jsonify({
                'success': False,
                'error': 'RATE_LIMIT_EXCEEDED',
                'message': 'Too many requests. Please try again later.',
                'retry_after': 60
            }), 429
        except BookingError as e:
            logger.error(f"Booking error: {e.message}")
            return jsonify({
                'success': False,
                'error': 'BOOKING_ERROR',
                'message': e.message,
                'details': e.response
            }), 400
        except AmadeusAPIError as e:
            logger.error(f"Amadeus API error: {e.message}")
            return jsonify({
                'success': False,
                'error': 'API_ERROR',
                'message': 'Unable to process your request. Please try again.',
                'technical_details': e.message if current_app.debug else None
            }), 500
        except Exception as e:
            logger.exception("Unexpected error in API endpoint")
            return jsonify({
                'success': False,
                'error': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred. Please try again later.'
            }), 500
    return decorated_function


def log_audit(user_id, action, entity_type, entity_id, description, changes=None):
    """Helper to log audit entries"""
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            changes=changes,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {str(e)}")


def map_travel_class(frontend_class: str) -> AmadeusTravelClass:
    """Map frontend travel class to Amadeus enum"""
    mapping = {
        'ECONOMY': AmadeusTravelClass.ECONOMY,
        'PREMIUM_ECONOMY': AmadeusTravelClass.PREMIUM_ECONOMY,
        'BUSINESS': AmadeusTravelClass.BUSINESS,
        'FIRST': AmadeusTravelClass.FIRST
    }
    return mapping.get(frontend_class.upper(), AmadeusTravelClass.ECONOMY)


# ==================== SEARCH ENDPOINTS ====================

@bp.route('/search/locations', methods=['GET'])
@handle_api_error
def search_locations():
    """
    Search for cities and airports by keyword
    
    Query Params:
        keyword (str): Search term (min 2 chars)
    """
    keyword = request.args.get('keyword', '').strip()
    
    if len(keyword) < 2:
        return jsonify({
            'success': True,
            'data': []
        }), 200
        
    try:
        amadeus_service = create_amadeus_service()
        locations = amadeus_service.search_locations(keyword)
        
        return jsonify({
            'success': True,
            'data': locations
        }), 200
        
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error in location search: {str(e)}")
        # For autocomplete, we often return empty struct on error to not break UI type-ahead
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'Failed to search locations'
        }), 500

@bp.route('/search', methods=['POST'])
@handle_api_error
def search_flights():
    """
    Search for flight offers
    
    Request Body:
    {
        "origin": "JFK",
        "destination": "LAX",
        "departureDate": "2025-03-15",
        "returnDate": "2025-03-20",  // optional
        "adults": 1,
        "children": 0,  // optional
        "infants": 0,  // optional
        "travelClass": "ECONOMY",  // optional
        "nonStop": false,  // optional
        "maxPrice": 1000,  // optional
        "currency": "USD"  // optional
    }
    """
    data = request.get_json()
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
    except Exception:
        current_user_id = None
        user = None
    
    # if not user or not user.is_active:
    #     return APIResponse.unauthorized('User not found or inactive')
    
    # Validate required fields
    required = ['origin', 'destination', 'departureDate', 'adults']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({
            'success': False,
            'error': 'MISSING_FIELDS',
            'message': f'Missing required fields: {", ".join(missing)}'
        }), 400
    
    # Validate date format
    try:
        datetime.strptime(data['departureDate'], '%Y-%m-%d')
        if data.get('returnDate'):
            datetime.strptime(data['returnDate'], '%Y-%m-%d')
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'INVALID_DATE',
            'message': 'Dates must be in YYYY-MM-DD format'
        }), 400
    
    # Initialize Amadeus service
    amadeus = create_amadeus_service(
        client_id=current_app.config.get('AMADEUS_API_KEY'),
        client_secret=current_app.config.get('AMADEUS_SECRET_KEY'),
        environment=current_app.config.get('AMADEUS_ENV', 'test')
    )
    
    try:
        # Prepare search parameters
        search_params = {
            'origin': data['origin'].upper(),
            'destination': data['destination'].upper(),
            'departure_date': data['departureDate'],
            'adults': int(data['adults']),
            'return_date': data.get('returnDate'),
            'children': int(data.get('children', 0)),
            'infants': int(data.get('infants', 0)),
            'currency': data.get('currency', 'USD').upper(),
            'max_results': int(data.get('maxResults', 50))
        }
        
        # Add optional parameters
        if data.get('travelClass'):
            search_params['travel_class'] = map_travel_class(data['travelClass'])
        if data.get('nonStop') is not None:
            search_params['non_stop'] = bool(data['nonStop'])
        if data.get('maxPrice'):
            search_params['max_price'] = float(data['maxPrice'])
        
        # Search flights
        results = amadeus.search_flight_offers(**search_params)
        
        # Log search for analytics
        if user:
            log_audit(
                user_id=user.id,
                action='FLIGHT_SEARCH',
                entity_type='search',
                entity_id=None,
                description=f"Searched flights {data['origin']} -> {data['destination']}"
            )
        
        return jsonify({
            'success': True,
            'data': results.get('data', []),
            'meta': results.get('meta', {}),
            'dictionaries': results.get('dictionaries', {})
        }), 200
        
    finally:
        amadeus.close()


@bp.route('/search/multi-city', methods=['POST'])
@handle_api_error
def search_multi_city():
    """
    Search for multi-city flight offers
    
    Request Body:
    {
        "segments": [
            {
                "origin": "MAD",
                "destination": "PAR",
                "departureDate": "2025-03-15"
            },
            {
                "origin": "PAR",
                "destination": "MUC",
                "departureDate": "2025-03-20"
            }
        ],
        "adults": 1,
        "children": 0,
        "travelClass": "ECONOMY"
    }
    """
    data = request.get_json()
    
    if not data.get('segments') or len(data['segments']) < 2:
        return jsonify({
            'success': False,
            'error': 'INVALID_SEGMENTS',
            'message': 'At least 2 segments required for multi-city search'
        }), 400
    
    # Build origin-destinations
    origin_destinations = []
    for i, segment in enumerate(data['segments']):
        origin_destinations.append({
            'id': str(i + 1),
            'originLocationCode': segment['origin'].upper(),
            'destinationLocationCode': segment['destination'].upper(),
            'departureDateTimeRange': {'date': segment['departureDate']}
        })
    
    # Build travelers
    travelers = []
    for i in range(int(data.get('adults', 1))):
        travelers.append({'id': str(i + 1), 'travelerType': 'ADULT'})
    
    child_count = int(data.get('children', 0))
    for i in range(child_count):
        travelers.append({'id': str(len(travelers) + 1), 'travelerType': 'CHILD'})
    
    # Search criteria
    search_criteria = {
        'maxFlightOffers': int(data.get('maxResults', 50))
    }
    
    if data.get('travelClass'):
        search_criteria['flightFilters'] = {
            'cabinRestrictions': [{
                'cabin': data['travelClass'].upper(),
                'coverage': 'MOST_SEGMENTS',
                'originDestinationIds': [str(i + 1) for i in range(len(origin_destinations))]
            }]
        }
    
    amadeus = create_amadeus_service(
        client_id=current_app.config.get('AMADEUS_CLIENT_ID'),
        client_secret=current_app.config.get('AMADEUS_CLIENT_SECRET'),
        environment=current_app.config.get('AMADEUS_ENV', 'test')
    )
    
    try:
        results = amadeus.search_flight_offers_post(
            origin_destinations=origin_destinations,
            travelers=travelers,
            search_criteria=search_criteria
        )
        
        return jsonify({
            'success': True,
            'data': results.get('data', []),
            'meta': results.get('meta', {}),
            'dictionaries': results.get('dictionaries', {})
        }), 200
        
    finally:
        amadeus.close()


# ==================== PRICING ENDPOINTS ====================

@bp.route('/price', methods=['POST'])
@handle_api_error
def confirm_price():
    """
    Confirm flight offer price before booking
    
    Request Body:
    {
        "flightOffers": [...],  // Flight offer(s) from search
        "include": ["credit-card-fees", "bags"]  // optional
    }
    """
    data = request.get_json()
    
    if not data.get('flightOffers'):
        return jsonify({
            'success': False,
            'error': 'MISSING_FLIGHT_OFFERS',
            'message': 'Flight offers are required'
        }), 400
    
    amadeus = create_amadeus_service(
        client_id=current_app.config.get('AMADEUS_CLIENT_ID'),
        client_secret=current_app.config.get('AMADEUS_CLIENT_SECRET'),
        environment=current_app.config.get('AMADEUS_ENV', 'test')
    )
    
    try:
        results = amadeus.confirm_flight_price(
            flight_offers=data['flightOffers'],
            include=data.get('include')
        )
        
        return jsonify({
            'success': True,
            'data': results.get('data', {}),
            'warnings': results.get('warnings', []),
            'dictionaries': results.get('dictionaries', {})
        }), 200
        
    finally:
        amadeus.close()


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
                "email": "[email protected]",
                "phone": {
                    "countryCode": "1",
                    "number": "5551234567"
                },
                "documents": [{
                    "documentType": "PASSPORT",
                    "number": "00000000",
                    "expiryDate": "2025-04-14",
                    "issuanceCountry": "US",
                    "nationality": "US"
                }]
            }
        ],
        "paymentMethod": "card",
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
        
        # Calculate service fee (e.g., 5% of base price)
        service_fee = base_price * Decimal('0.05')
        final_total = total_price + service_fee
        
        # Create booking
        booking = Booking(
            user_id=user.id,
            booking_type=BookingType.FLIGHT.value,
            status=BookingStatus.PENDING,
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
            travel_class=TravelClass.ECONOMY,  # Extract from validatingAirlineCodes or travelerPricings
            num_adults=len([t for t in data['travelers'] if t.get('travelerType', 'ADULT') == 'ADULT']),
            num_children=len([t for t in data['travelers'] if t.get('travelerType') == 'CHILD']),
            num_infants=len([t for t in data['travelers'] if t.get('travelerType') == 'INFANT']),
            base_price=base_price,
            service_fee=service_fee,
            taxes=taxes,
            total_price=final_total,
            special_requests=data.get('specialRequests'),
            assigned_agent_id=None  # Can be assigned later
        )
        
        db.session.add(booking)
        db.session.flush()  # Get booking ID
        
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
                special_assistance=traveler_data.get('specialAssistance')
            )
            db.session.add(passenger)
        
        # Create payment record
        payment = Payment(
            booking_id=booking.id,
            user_id=user.id,
            amount=final_total,
            currency=price.get('currency', 'USD'),
            payment_method=data.get('paymentMethod', 'card'),
            status=PaymentStatus.PENDING
        )
        db.session.add(payment)
        
        # Commit to database
        db.session.commit()
        
        # Log audit
        log_audit(
            user_id=user.id,
            action='BOOKING_CREATED',
            entity_type='booking',
            entity_id=booking.id,
            description=f"Created booking {booking.booking_reference}"
        )
        
        # Return booking details for payment
        return jsonify({
            'success': True,
            'message': 'Booking created successfully',
            'data': {
                'bookingId': booking.id,
                'bookingReference': booking.booking_reference,
                'paymentId': payment.id,
                'amount': float(final_total),
                'currency': price.get('currency', 'USD'),
                'status': booking.status.value
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
        # Process payment (integrate with actual payment service)
        payment_service = PaymentService(current_app.config)
        payment_result = payment_service.confirm_payment(
            payment_intent_id=data.get('paymentIntentId'),
            amount=float(payment.amount),
            currency=payment.currency
        )
        
        if payment_result.get('status') == 'succeeded':
            payment.status = PaymentStatus.PAID
            payment.paid_at = datetime.now(timezone.utc)
            payment.stripe_payment_intent_id = data.get('paymentIntentId')
            payment.transaction_id = payment_result.get('transactionId')
            
            # Update booking status
            booking.status = BookingStatus.CONFIRMED
            booking.confirmed_at = datetime.now(timezone.utc)
            
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
                action='BOOKING_CONFIRMED',
                entity_type='booking',
                entity_id=booking.id,
                description=f"Confirmed booking {booking.booking_reference}"
            )
            
            return jsonify({
                'success': True,
                'message': 'Booking confirmed successfully',
                'data': {
                    'bookingReference': booking.booking_reference,
                    'status': booking.status.value,
                    'confirmationNumber': booking.airline_confirmation
                }
            }), 200
        else:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = payment_result.get('error', 'Payment failed')
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': 'PAYMENT_FAILED',
                'message': 'Payment processing failed. Please try again.'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to confirm booking")
        raise


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