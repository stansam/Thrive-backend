import pytest
from unittest.mock import MagicMock, patch
from app.models.enums import BookingStatus, BookingType, TravelClass
from app.models.booking import Booking
from app.models.passenger import Passenger
from app.models.payment import Payment

@pytest.fixture
def auth_headers(client, db):
    # Create a user
    from app.models.user import User
    user = User(
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()

    # Login to get token
    response = client.post('/api/auth/login', json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = response.get_json()['data']['tokens']['accessToken']
    return {"Authorization": f"Bearer {token}"}

def test_create_booking_request_flow(client, auth_headers, db):
    """
    Test the new booking flow where:
    1. Booking is created with status REQUESTED
    2. No payment record is created immediately
    3. Service fee is calculated but not charged yet
    """
    
    # Mock data
    booking_payload = {
        "flightOffers": [{
            "itineraries": [{
                "segments": [
                    {
                        "departure": {"iataCode": "JFK", "at": "2023-12-01T10:00:00"},
                        "arrival": {"iataCode": "LHR", "at": "2023-12-01T22:00:00"},
                        "carrierCode": "BA",
                        "number": "112"
                    }
                ]
            }],
            "price": {
                "currency": "USD",
                "total": "1000.00",
                "base": "800.00"
            },
            "travelerPricings": [
                {"travelerId": "1", "travelerType": "ADULT", "price": {"currency": "USD", "total": "1000.00"}}
            ]
        }],
        "travelers": [
            {
                "id": "1",
                "travelerType": "ADULT",
                "firstName": "John",
                "lastName": "Doe",
                "dateOfBirth": "1990-01-01",
                "gender": "MALE",
                "email": "john@example.com",
                "phone": {"countryCode": "1", "number": "5555555555"},
                "documents": [{
                    "documentType": "PASSPORT",
                    "number": "A12345678",
                    "expiryDate": "2030-01-01",
                    "issuanceCountry": "US",
                    "nationality": "US",
                    "holder": True
                }],
                "selectedSeats": { "1": "12A" } 
            }
        ],
        "specialRequests": "Vegetarian meal"
    }

    # Mock Amadeus confirm_flight_price since the endpoint calls it
    # AND mock the internal booking creation logic if needed, but we want integration test.
    # The endpoint calls `amadeus.confirm_flight_price`. We must mock that.
    
    with patch('app.api.flights.booking.create_amadeus_service') as mock_create_service:
        mock_amadeus = MagicMock()
        mock_create_service.return_value = mock_amadeus
        
        # Mock confirmation response (returns input offer usually)
        mock_amadeus.confirm_flight_price.return_value = {
            "data": {
                "flightOffers": booking_payload["flightOffers"]
            }
        }
        
        # Make Request
        response = client.post('/api/flights/book', json=booking_payload, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['status'] == 'requested'
        assert data['data']['bookingReference'] == 'PENDING'
        
        booking_id = data['data']['bookingId']
        
        # Verify DB State
        booking = db.session.get(Booking, booking_id)
        assert booking is not None
        assert booking.status == BookingStatus.REQUESTED
        assert booking.origin == "JFK"
        assert booking.destination == "LHR"
        
        # Verify Passenger
        passenger = db.session.query(Passenger).filter_by(booking_id=booking_id).first()
        assert passenger is not None
        assert passenger.first_name == "John"
        # Check if seat selection was captured in special_assistance as implemented
        assert "Seats: 1:12A" in passenger.special_assistance
        
        # Verify NO Payment created
        payment = db.session.query(Payment).filter_by(booking_id=booking_id).first()
        assert payment is None
