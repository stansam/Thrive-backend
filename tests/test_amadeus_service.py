import pytest
from app.services.amadeus import create_amadeus_service, AmadeusEnvironment, AmadeusConfig, AmadeusFlightService, AmadeusAPIError
from unittest.mock import patch, MagicMock

@pytest.fixture
def amadeus_service():
    config = AmadeusConfig(
        client_id="test_id",
        client_secret="test_secret",
        environment=AmadeusEnvironment.TEST
    )
    # We patch requests.Session inside the __init__ or use 'responses' library which mocks adapter
    # But AmadeusFlightService uses requests.Session().
    # Let's mock the session object created in __init__?
    
    from datetime import datetime, timedelta
    with patch('app.services.amadeus.AmadeusFlightService._authenticate'):
         service = AmadeusFlightService(config)
         service._access_token = "fake_token"
         service._token_expiry = datetime.now() + timedelta(hours=1)
    
    return service

def test_search_flight_offers(amadeus_service):
    # Mock the session.get method
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"id": "1", "itineraries": []}]
    }
    
    with patch.object(amadeus_service._session, 'get', return_value=mock_response) as mock_get:
        result = amadeus_service.search_flight_offers(
            origin="JFK",
            destination="LHR",
            departure_date="2024-12-25"
        )
        
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == '1'
        mock_get.assert_called_once()
        
        # Verify URL and params
        args, kwargs = mock_get.call_args
        assert "/v2/shopping/flight-offers" in args[0]
        assert kwargs['params']['originLocationCode'] == 'JFK'

def test_search_flight_offers_error(amadeus_service):
    # Mock error response
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "errors": [{"title": "Invalid Parameter", "detail": "Invalid Date"}]
    }
    mock_response.text = '{"errors": ...}' # for safe extraction check if used
    
    with patch.object(amadeus_service._session, 'get', return_value=mock_response):
        with pytest.raises(AmadeusAPIError) as excinfo:
             amadeus_service.search_flight_offers(
                origin="JFK",
                destination="LHR",
                departure_date="invalid"
            )
        assert "Invalid Parameter" in str(excinfo.value)

def test_confirm_flight_price(amadeus_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {"flightOffers": [{"id": "1", "price": {"total": "100.00"}}]}
    }
    
    with patch.object(amadeus_service._session, 'post', return_value=mock_response) as mock_post:
        offers = [{"id": "1"}]
        result = amadeus_service.confirm_flight_price(offers)
        
        assert "flightOffers" in result['data']
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "/pricing" in args[0]
        assert kwargs['json']['data']['type'] == 'flight-offers-pricing'

def test_create_flight_order(amadeus_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {"id": "booking_123"}
    }
    
    with patch.object(amadeus_service._session, 'post', return_value=mock_response) as mock_post:
        offers = [{"id": "1"}]
        travelers = [{"id": "1"}]
        
        result = amadeus_service.create_flight_order(offers, travelers)
        
        assert result['data']['id'] == "booking_123"
        mock_post.assert_called_once()
        
