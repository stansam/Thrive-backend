from flask import request, jsonify, current_app
from app.services.amadeus import create_amadeus_service
from app.api.flights import flights_bp as bp
from .utils import handle_api_error

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
