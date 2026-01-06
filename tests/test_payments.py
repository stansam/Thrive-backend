# tests/test_payments.py
import pytest
from unittest.mock import patch, MagicMock
from app.models.user import User
from app.models.booking import Booking
from app.models.enums import BookingStatus

@pytest.fixture
def seed_data(app, db):
    with app.app_context():
        user = User(
            email="[email protected]", 
            password_hash="hash",
            first_name="Test",
            last_name="User"
        )
        db.session.add(user)
        db.session.commit()
        
        booking = Booking(
            user_id=user.id,
            booking_reference="REF123",
            booking_type='flight',
            base_price=90.00,
            service_fee=10.00,
            total_price=100.00,
            status=BookingStatus.PENDING,
            origin="JFK",
            destination="LAX"
        )
        db.session.add(booking)
        db.session.commit()
        
        return user.id, booking.id

@pytest.fixture
def auth_header(app, seed_data):
    user_id, _ = seed_data
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=user_id)
        return {'Authorization': f'Bearer {token}'}

def test_create_payment_intent(client, seed_data, auth_header):
    user_id, booking_id = seed_data
    
    # Mock PaymentService
    mock_service_instance = MagicMock()
    mock_service_instance.create_payment_intent.return_value = {
        'success': True,
        'paymentIntentId': 'pi_123',
        'clientSecret': 'secret_123'
    }
    
    with patch('app.api.payments.routes.PaymentService', return_value=mock_service_instance):
        response = client.post('/api/payments/create-intent', json={
            'bookingId': str(booking_id),
            'amount': 100.00,
            'currency': 'USD'
        }, headers=auth_header)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['clientSecret'] == 'secret_123'

def test_create_payment_intent_amount_mismatch(client, seed_data, auth_header):
    user_id, booking_id = seed_data
    
    response = client.post('/api/payments/create-intent', json={
        'bookingId': str(booking_id),
        'amount': 50.00, # mismatch
        'currency': 'USD'
    }, headers=auth_header)
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'AMOUNT_MISMATCH'
