from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required
import logging

from app.services.amadeus import create_amadeus_service
from app.api.flights import flights_bp as bp
from app.utils.api_response import APIResponse
from app.api.flights.utils import handle_api_error

logger = logging.getLogger(__name__)

@bp.route('/seatmap', methods=['POST'])
@jwt_required()
@handle_api_error
def get_seatmap_endpoint():
    """
    Get seat map for a flight offer
    
    Request Body:
    {
        "flightOffer": {...}
    }
    """
    data = request.get_json()
    flight_offer = data.get('flightOffer')
    
    if not flight_offer:
        return jsonify({
            'success': False,
            'error': 'MISSING_DATA',
            'message': 'Flight offer data is required'
        }), 400
        
    amadeus = create_amadeus_service(
        client_id=current_app.config.get('AMADEUS_API_KEY'),
        client_secret=current_app.config.get('AMADEUS_SECRET_KEY'),
        environment=current_app.config.get('AMADEUS_ENV', 'test')
    )
    
    seatmaps = amadeus.get_seatmap(flight_offer)
    
    return jsonify({
        'success': True,
        'data': seatmaps
    }), 200
