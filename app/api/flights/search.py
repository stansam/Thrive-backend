from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity
from datetime import datetime
import logging

from app.models.user import User
from app.services.amadeus import create_amadeus_service
from app.api.flights import flights_bp as bp
from .utils import handle_api_error, log_audit, map_travel_class

logger = logging.getLogger(__name__)

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
