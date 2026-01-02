"""
Comprehensive tests for dashboard client API endpoints
Run with: pytest tests/test_dashboard.py -v
"""
import pytest
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app import create_app, db
from app.models import User, Booking, Package, Payment, Notification
from app.models.enums import UserRole, SubscriptionTier, BookingStatus, PaymentStatus, TripType, TravelClass
from config import Config


class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'
    STRIPE_SECRET_KEY = 'sk_test_fake_key_for_testing'
    STRIPE_PUBLISHABLE_KEY = 'pk_test_fake_key_for_testing'


@pytest.fixture
def app():
    """Create and configure test app"""
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing"""
    with app.app_context():
        user = User(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            phone='+1234567890',
            role=UserRole.CUSTOMER,
            subscription_tier=SubscriptionTier.NONE,
            email_verified=True,
            is_active=True,
            referral_code='TEST123456',
            referral_credits=Decimal('0.00')
        )
        user.set_password('TestPass123')
        
        db.session.add(user)
        db.session.commit()
        
        return user


@pytest.fixture
def auth_headers(client, sample_user):
    """Get authentication headers"""
    response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'TestPass123'
    })
    data = json.loads(response.data)
    access_token = data['data']['tokens']['accessToken']
    
    return {'Authorization': f'Bearer {access_token}'}


@pytest.fixture
def sample_booking(app, sample_user):
    """Create a sample booking"""
    with app.app_context():
        booking = Booking(
            user_id=sample_user.id,
            booking_reference='TGT-TEST123',
            booking_type='flight',
            status=BookingStatus.CONFIRMED,
            trip_type=TripType.ROUND_TRIP,
            origin='New York',
            destination='London',
            departure_date=datetime.now(timezone.utc) + timedelta(days=30),
            return_date=datetime.now(timezone.utc) + timedelta(days=37),
            airline='British Airways',
            flight_number='BA123',
            travel_class=TravelClass.ECONOMY,
            num_adults=2,
            num_children=0,
            num_infants=0,
            base_price=Decimal('800.00'),
            service_fee=Decimal('50.00'),
            taxes=Decimal('150.00'),
            discount=Decimal('0.00'),
            total_price=Decimal('1000.00')
        )
        
        db.session.add(booking)
        db.session.commit()
        
        return booking


class TestDashboardSummary:
    """Test dashboard summary endpoint"""
    
    def test_get_dashboard_summary(self, client, auth_headers, sample_user, sample_booking):
        """Test successful dashboard summary retrieval"""
        response = client.get('/api/client/dashboard/summary', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'stats' in data['data']
        assert 'recentBookings' in data['data']
        assert 'chartData' in data['data']
        assert data['data']['stats']['totalBookings'] >= 1
    
    def test_dashboard_summary_unauthorized(self, client):
        """Test dashboard summary without authentication"""
        response = client.get('/api/client/dashboard/summary')
        
        assert response.status_code == 401


class TestProfileManagement:
    """Test profile management endpoints"""
    
    def test_get_profile(self, client, auth_headers, sample_user):
        """Test successful profile retrieval"""
        response = client.get('/api/client/dashboard/profile', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['profile']['email'] == 'test@example.com'
        assert data['data']['profile']['firstName'] == 'Test'
        assert data['data']['profile']['lastName'] == 'User'
    
    def test_update_profile(self, client, auth_headers):
        """Test successful profile update"""
        response = client.put('/api/client/dashboard/profile', 
            headers=auth_headers,
            json={
                'firstName': 'Updated',
                'lastName': 'Name',
                'phone': '+9876543210',
                'nationality': 'American'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['profile']['firstName'] == 'Updated'
    
    def test_update_profile_invalid_phone(self, client, auth_headers):
        """Test profile update with invalid phone"""
        response = client.put('/api/client/dashboard/profile',
            headers=auth_headers,
            json={
                'phone': 'invalid'
            }
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'phone' in data['errors']
    
    def test_update_profile_invalid_dob(self, client, auth_headers):
        """Test profile update with future date of birth"""
        response = client.put('/api/client/dashboard/profile',
            headers=auth_headers,
            json={
                'dateOfBirth': '2030-01-01'
            }
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'dateOfBirth' in data['errors']


class TestSubscriptionManagement:
    """Test subscription management endpoints"""
    
    def test_get_subscriptions(self, client, auth_headers):
        """Test successful subscriptions retrieval"""
        response = client.get('/api/client/dashboard/subscriptions', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'currentSubscription' in data['data']
        assert 'availableTiers' in data['data']
        assert 'bronze' in data['data']['availableTiers']
        assert 'silver' in data['data']['availableTiers']
        assert 'gold' in data['data']['availableTiers']
    
    def test_upgrade_subscription_invalid_tier(self, client, auth_headers):
        """Test subscription upgrade with invalid tier"""
        response = client.post('/api/client/dashboard/subscriptions/upgrade',
            headers=auth_headers,
            json={
                'tier': 'platinum'
            }
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'tier' in data['errors']


class TestBookingsManagement:
    """Test bookings management endpoints"""
    
    def test_get_bookings(self, client, auth_headers, sample_booking):
        """Test successful bookings retrieval"""
        response = client.get('/api/client/dashboard/bookings', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'bookings' in data['data']
        assert 'pagination' in data['data']
        assert len(data['data']['bookings']) >= 1
    
    def test_get_bookings_with_filters(self, client, auth_headers, sample_booking):
        """Test bookings retrieval with filters"""
        response = client.get('/api/client/dashboard/bookings?status=confirmed&type=flight',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_get_bookings_pagination(self, client, auth_headers, sample_booking):
        """Test bookings pagination"""
        response = client.get('/api/client/dashboard/bookings?page=1&perPage=5',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['pagination']['page'] == 1
        assert data['data']['pagination']['perPage'] == 5
    
    def test_get_booking_details(self, client, auth_headers, sample_booking):
        """Test successful booking details retrieval"""
        response = client.get(f'/api/client/dashboard/bookings/{sample_booking.id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['booking']['id'] == sample_booking.id
        assert 'passengers' in data['data']['booking']
        assert 'payments' in data['data']['booking']
    
    def test_get_booking_details_not_found(self, client, auth_headers):
        """Test booking details with non-existent booking"""
        response = client.get('/api/client/dashboard/bookings/nonexistent-id',
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_cancel_booking(self, client, auth_headers, sample_booking):
        """Test successful booking cancellation"""
        response = client.post(f'/api/client/dashboard/bookings/{sample_booking.id}/cancel',
            headers=auth_headers,
            json={
                'reason': 'Change of plans',
                'requestRefund': True
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['booking']['status'] in ['cancelled', 'refunded']
    
    def test_cancel_already_cancelled_booking(self, client, auth_headers, app, sample_booking):
        """Test cancelling an already cancelled booking"""
        # First cancellation
        client.post(f'/api/client/dashboard/bookings/{sample_booking.id}/cancel',
            headers=auth_headers,
            json={'reason': 'Test'}
        )
        
        # Second cancellation attempt
        response = client.post(f'/api/client/dashboard/bookings/{sample_booking.id}/cancel',
            headers=auth_headers,
            json={'reason': 'Test again'}
        )
        
        assert response.status_code == 400


class TestTripsManagement:
    """Test trips management endpoints"""
    
    def test_get_trips(self, client, auth_headers):
        """Test successful trips retrieval"""
        response = client.get('/api/client/dashboard/trips', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'trips' in data['data']
        assert 'pagination' in data['data']
    
    def test_get_trips_with_status_filter(self, client, auth_headers):
        """Test trips retrieval with status filter"""
        response = client.get('/api/client/dashboard/trips?status=active',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestContactForm:
    """Test contact form endpoint"""
    
    def test_submit_contact_form(self, client, auth_headers):
        """Test successful contact form submission"""
        response = client.post('/api/client/dashboard/contact',
            headers=auth_headers,
            json={
                'category': 'general',
                'subject': 'Test inquiry',
                'message': 'This is a test message that is long enough to pass validation requirements.'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_submit_contact_form_invalid_category(self, client, auth_headers):
        """Test contact form with invalid category"""
        response = client.post('/api/client/dashboard/contact',
            headers=auth_headers,
            json={
                'category': 'invalid',
                'subject': 'Test',
                'message': 'This is a test message.'
            }
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'category' in data['errors']
    
    def test_submit_contact_form_short_message(self, client, auth_headers):
        """Test contact form with too short message"""
        response = client.post('/api/client/dashboard/contact',
            headers=auth_headers,
            json={
                'category': 'general',
                'subject': 'Test',
                'message': 'Short'
            }
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'message' in data['errors']


class TestNotifications:
    """Test notifications endpoints"""
    
    def test_get_notifications(self, client, auth_headers, app, sample_user):
        """Test successful notifications retrieval"""
        # Create a test notification
        with app.app_context():
            notification = Notification(
                user_id=sample_user.id,
                type='test',
                title='Test Notification',
                message='This is a test notification',
                is_read=False
            )
            db.session.add(notification)
            db.session.commit()
        
        response = client.get('/api/client/dashboard/notifications', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'notifications' in data['data']
        assert len(data['data']['notifications']) >= 1
    
    def test_get_unread_notifications(self, client, auth_headers):
        """Test unread notifications retrieval"""
        response = client.get('/api/client/dashboard/notifications?unreadOnly=true',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_mark_notification_read(self, client, auth_headers, app, sample_user):
        """Test marking notification as read"""
        # Create a test notification
        with app.app_context():
            notification = Notification(
                user_id=sample_user.id,
                type='test',
                title='Test',
                message='Test message',
                is_read=False
            )
            db.session.add(notification)
            db.session.commit()
            notification_id = notification.id
        
        response = client.put(f'/api/client/dashboard/notifications/{notification_id}/read',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['notification']['is_read'] is True


class TestValidationSchemas:
    """Test validation schema edge cases"""
    
    def test_profile_update_passport_expiry_past(self, client, auth_headers):
        """Test profile update with past passport expiry"""
        response = client.put('/api/client/dashboard/profile',
            headers=auth_headers,
            json={
                'passportExpiry': '2020-01-01'
            }
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'passportExpiry' in data['errors']
    
    def test_booking_filters_invalid_date_range(self, client, auth_headers):
        """Test booking filters with invalid date range"""
        response = client.get('/api/client/dashboard/bookings?startDate=2024-12-31&endDate=2024-01-01',
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'dateRange' in data['errors']
    
    def test_booking_filters_invalid_page(self, client, auth_headers):
        """Test booking filters with invalid page number"""
        response = client.get('/api/client/dashboard/bookings?page=0',
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'page' in data['errors']


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
