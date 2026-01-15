# tests/test_flights.py
import pytest
from unittest.mock import patch, MagicMock
from app.models.user import User

@pytest.fixture
def auth_header(app, db):
    from flask_jwt_extended import create_access_token
    with app.app_context():
        user = User(
            email="[email protected]", 
            password_hash="hash",
            first_name="Test",
            last_name="User"
        )
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=user.id)
        return {'Authorization': f'Bearer {token}'}

def test_flight_search(client, auth_header):
    # Mock create_amadeus_service
    mock_service = MagicMock()
    mock_service.search_flight_offers.return_value = {
        'data': [{'id': '1'}], 'meta': {}, 'dictionaries': {}
    }
    
    with patch('app.api.flights.search.create_amadeus_service', return_value=mock_service):
        response = client.post('/api/flights/search', json={
            'origin': 'JFK',
            'destination': 'LAX',
            'departureDate': '2026-01-15',
            'adults': 1
        }, headers=auth_header)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 1

def test_flight_search_missing_fields(client):
    response = client.post('/api/flights/search', json={
        'origin': 'JFK'
    })
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'MISSING_FIELDS'

def test_confirm_price(client, auth_header):
    mock_service = MagicMock()
    mock_service.confirm_flight_price.return_value = {
        'data': {'flightOffers': [{'id': '1', 'price': {'total': '100'}}]}
    }
    
    with patch('app.api.flights.pricing.create_amadeus_service', return_value=mock_service):
        response = client.post('/api/flights/price', json={
            'flightOffers': [{'id': '1'}]
        }, headers=auth_header)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['flightOffers'][0]['price']['total'] == '100'

def test_create_booking(client, auth_header):
    mock_service = MagicMock()
    mock_service.create_flight_order.return_value = {
        'data': {'id': 'order_123', 'associatedRecords': [{'reference': 'REF123'}]}
    }
    
    with patch('app.api.flights.booking.create_amadeus_service', return_value=mock_service):
        response = client.post('/api/flights/book', json={
            'flightOffers': [{
                'id': '1', 
                'price': {'currency': 'USD', 'base': '90.00', 'total': '100.00'},
                'itineraries': [{
                    'segments': [{
                        'departure': {'iataCode': 'JFK', 'at': '2026-01-01T10:00:00'},
                        'arrival': {'iataCode': 'LAX', 'at': '2026-01-01T14:00:00'},
                        'carrierCode': 'AA',
                        'number': '100'
                    }]
                }]
            }],
            'travelers': [{'id': '1', 'firstName': 'Test', 'lastName': 'User', 'dateOfBirth': '1990-01-01', 'gender': 'MALE', 'email': '[email protected]', 'phone': {'countryCode': '1', 'number': '5555555555'}}],
            'paymentMethod': 'card'
        }, headers=auth_header)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['bookingId'] is not None