"""
Comprehensive tests for admin API endpoints
Run with: pytest tests/test_admin.py -v
"""
import pytest
import json
from datetime import datetime
from app import create_app, db
from app.models import User, Booking, Quote, Package, Payment, ContactMessage
from app.models.enums import UserRole, SubscriptionTier, BookingStatus, PaymentStatus
from config import Config


class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'


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
def admin_user(app):
    """Create admin user for testing"""
    with app.app_context():
        admin = User(
            email='admin@test.com',
            first_name='Admin',
            last_name='User',
            role=UserRole.ADMIN,
            subscription_tier=SubscriptionTier.NONE,
            email_verified=True,
            is_active=True
        )
        admin.set_password('AdminPass123')
        admin.referral_code = 'ADMIN123'
        
        db.session.add(admin)
        db.session.commit()
        
        return admin


@pytest.fixture
def regular_user(app):
    """Create regular user for testing"""
    with app.app_context():
        user = User(
            email='user@test.com',
            first_name='Regular',
            last_name='User',
            role=UserRole.CUSTOMER,
            subscription_tier=SubscriptionTier.BRONZE,
            email_verified=True,
            is_active=True
        )
        user.set_password('UserPass123')
        user.referral_code = 'USER123'
        
        db.session.add(user)
        db.session.commit()
        
        return user


@pytest.fixture
def admin_token(client, admin_user):
    """Get admin auth token"""
    response = client.post('/api/auth/login', json={
        'email': 'admin@test.com',
        'password': 'AdminPass123'
    })
    data = json.loads(response.data)
    return data['data']['tokens']['accessToken']


@pytest.fixture
def user_token(client, regular_user):
    """Get regular user auth token"""
    response = client.post('/api/auth/login', json={
        'email': 'user@test.com',
        'password': 'UserPass123'
    })
    data = json.loads(response.data)
    return data['data']['tokens']['accessToken']


# ===== AUTHORIZATION TESTS =====

class TestAdminAuthorization:
    """Test admin-only access control"""
    
    def test_admin_dashboard_requires_authentication(self, client):
        """Test that dashboard requires authentication"""
        response = client.get('/api/admin/dashboard')
        assert response.status_code == 401
    
    def test_admin_dashboard_requires_admin_role(self, client, user_token):
        """Test that regular users cannot access admin dashboard"""
        response = client.get('/api/admin/dashboard',
            headers={'Authorization': f'Bearer {user_token}'}
        )
        assert response.status_code == 403
        data = json.loads(response.data)
        assert 'admin' in data['message'].lower()
    
    def test_admin_dashboard_accessible_by_admin(self, client, admin_token):
        """Test that admin can access dashboard"""
        response = client.get('/api/admin/dashboard',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200


# ===== DASHBOARD TESTS =====

class TestAdminDashboard:
    """Test admin dashboard endpoint"""
    
    def test_get_dashboard_stats(self, client, admin_token, regular_user):
        """Test dashboard returns correct statistics"""
        response = client.get('/api/admin/dashboard',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        
        assert 'stats' in data
        assert 'totalUsers' in data['stats']
        assert 'totalBookings' in data['stats']
        assert 'totalRevenue' in data['stats']
        assert 'recentBookings' in data
        assert 'revenueChart' in data


# ===== USER MANAGEMENT TESTS =====

class TestUserManagement:
    """Test user management endpoints"""
    
    def test_list_users(self, client, admin_token, regular_user):
        """Test listing users with pagination"""
        response = client.get('/api/admin/users?page=1&perPage=20',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert 'users' in data
        assert 'pagination' in data
        assert len(data['users']) >= 1  # At least admin user
    
    def test_search_users(self, client, admin_token, regular_user):
        """Test user search functionality"""
        response = client.get('/api/admin/users?search=regular',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert len(data['users']) >= 1
        assert any('regular' in user['first_name'].lower() for user in data['users'])
    
    def test_filter_users_by_role(self, client, admin_token, regular_user):
        """Test filtering users by role"""
        response = client.get('/api/admin/users?role=customer',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        for user in data['users']:
            assert user['role'] == 'customer'
    
    def test_get_user_details(self, client, admin_token, regular_user, app):
        """Test getting detailed user information"""
        with app.app_context():
            user_id = User.query.filter_by(email='user@test.com').first().id
        
        response = client.get(f'/api/admin/users/{user_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert 'user' in data
        assert data['user']['email'] == 'user@test.com'
        assert 'totalBookings' in data['user']
        assert 'totalSpent' in data['user']
    
    def test_update_user(self, client, admin_token, regular_user, app):
        """Test updating user details"""
        with app.app_context():
            user_id = User.query.filter_by(email='user@test.com').first().id
        
        response = client.patch(f'/api/admin/users/{user_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'role': 'corporate',
                'subscriptionTier': 'silver'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert data['user']['role'] == 'corporate'
        assert data['user']['subscription_tier'] == 'silver'
    
    def test_deactivate_user(self, client, admin_token, regular_user, app):
        """Test deactivating user account"""
        with app.app_context():
            user_id = User.query.filter_by(email='user@test.com').first().id
        
        response = client.delete(f'/api/admin/users/{user_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        
        # Verify user is deactivated
        with app.app_context():
            user = User.query.get(user_id)
            assert user.is_active == False
    
    def test_update_nonexistent_user(self, client, admin_token):
        """Test updating non-existent user returns 404"""
        response = client.patch('/api/admin/users/nonexistent-id',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'role': 'admin'}
        )
        
        assert response.status_code == 404


# ===== BOOKING MANAGEMENT TESTS =====

class TestBookingManagement:
    """Test booking management endpoints"""
    
    @pytest.fixture
    def sample_booking(self, app, regular_user):
        """Create sample booking"""
        with app.app_context():
            booking = Booking(
                user_id=regular_user.id,
                booking_type='flight',
                status=BookingStatus.PENDING,
                origin='JFK',
                destination='LAX',
                base_price=500.00,
                service_fee=50.00,
                total_price=550.00
            )
            db.session.add(booking)
            db.session.commit()
            return booking
    
    def test_list_bookings(self, client, admin_token, sample_booking):
        """Test listing bookings"""
        response = client.get('/api/admin/bookings',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert 'bookings' in data
        assert len(data['bookings']) >= 1
    
    def test_filter_bookings_by_status(self, client, admin_token, sample_booking):
        """Test filtering bookings by status"""
        response = client.get('/api/admin/bookings?status=pending',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        for booking in data['bookings']:
            assert booking['status'] == 'pending'
    
    def test_get_booking_details(self, client, admin_token, sample_booking, app):
        """Test getting booking details"""
        with app.app_context():
            booking_id = Booking.query.first().id
        
        response = client.get(f'/api/admin/bookings/{booking_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert 'booking' in data
        assert 'customer' in data['booking']
        assert 'payments' in data['booking']
    
    def test_update_booking_status(self, client, admin_token, sample_booking, app):
        """Test updating booking status"""
        with app.app_context():
            booking_id = Booking.query.first().id
        
        response = client.patch(f'/api/admin/bookings/{booking_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'status': 'confirmed'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert data['booking']['status'] == 'confirmed'
    
    def test_cancel_booking(self, client, admin_token, sample_booking, app):
        """Test cancelling booking"""
        with app.app_context():
            booking_id = Booking.query.first().id
        
        response = client.post(f'/api/admin/bookings/{booking_id}/cancel',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'reason': 'Customer request'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert data['booking']['status'] == 'cancelled'
    
    def test_get_booking_stats(self, client, admin_token, sample_booking):
        """Test getting booking statistics"""
        response = client.get('/api/admin/bookings/stats',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert 'totalBookings' in data
        assert 'bookingsByStatus' in data
        assert 'totalRevenue' in data


# ===== PACKAGE MANAGEMENT TESTS =====

class TestPackageManagement:
    """Test package management endpoints"""
    
    def test_create_package(self, client, admin_token):
        """Test creating new package"""
        response = client.post('/api/admin/packages',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Paris Adventure',
                'destinationCity': 'Paris',
                'destinationCountry': 'France',
                'durationDays': 7,
                'durationNights': 6,
                'startingPrice': 1500.00,
                'pricePerPerson': 1500.00,
                'description': 'Explore the city of lights'
            }
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)['data']
        assert 'package' in data
        assert data['package']['name'] == 'Paris Adventure'
    
    def test_list_packages(self, client, admin_token, app):
        """Test listing packages"""
        # Create a package first
        with app.app_context():
            package = Package(
                name='Test Package',
                slug='test-package',
                destination_city='Rome',
                destination_country='Italy',
                duration_days=5,
                duration_nights=4,
                starting_price=1000.00,
                price_per_person=1000.00,
                is_active=True
            )
            db.session.add(package)
            db.session.commit()
        
        response = client.get('/api/admin/packages',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert 'packages' in data
        assert len(data['packages']) >= 1
    
    def test_update_package(self, client, admin_token, app):
        """Test updating package"""
        with app.app_context():
            package = Package(
                name='Original Name',
                slug='original-name',
                destination_city='London',
                destination_country='UK',
                duration_days=4,
                duration_nights=3,
                starting_price=800.00,
                price_per_person=800.00
            )
            db.session.add(package)
            db.session.commit()
            package_id = package.id
        
        response = client.patch(f'/api/admin/packages/{package_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'name': 'Updated Name', 'startingPrice': 900.00}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert data['package']['name'] == 'Updated Name'


# ===== CONTACT MESSAGES TESTS =====

class TestContactMessages:
    """Test contact message management"""
    
    @pytest.fixture
    def sample_contact(self, app):
        """Create sample contact message"""
        with app.app_context():
            contact = ContactMessage(
                name='John Doe',
                email='john@example.com',
                subject='Question about booking',
                message='I have a question...',
                status='new',
                priority='normal'
            )
            db.session.add(contact)
            db.session.commit()
            return contact
    
    def test_list_contacts(self, client, admin_token, sample_contact):
        """Test listing contact messages"""
        response = client.get('/api/admin/contacts',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert 'contacts' in data
        assert len(data['contacts']) >= 1
    
    def test_filter_contacts_by_status(self, client, admin_token, sample_contact):
        """Test filtering contacts by status"""
        response = client.get('/api/admin/contacts?status=new',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        for contact in data['contacts']:
            assert contact['status'] == 'new'
    
    def test_update_contact_status(self, client, admin_token, sample_contact, app):
        """Test updating contact message"""
        with app.app_context():
            contact_id = ContactMessage.query.first().id
        
        response = client.patch(f'/api/admin/contacts/{contact_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'status': 'resolved',
                'adminNotes': 'Issue resolved via email'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert data['contact']['status'] == 'resolved'
    
    def test_delete_contact(self, client, admin_token, sample_contact, app):
        """Test deleting contact message"""
        with app.app_context():
            contact_id = ContactMessage.query.first().id
        
        response = client.delete(f'/api/admin/contacts/{contact_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        
        # Verify deletion
        with app.app_context():
            contact = ContactMessage.query.get(contact_id)
            assert contact is None


# ===== VALIDATION TESTS =====

class TestValidation:
    """Test input validation"""
    
    def test_invalid_user_update(self, client, admin_token, regular_user, app):
        """Test validation errors on user update"""
        with app.app_context():
            user_id = User.query.filter_by(email='user@test.com').first().id
        
        response = client.patch(f'/api/admin/users/{user_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'role': 'invalid_role'}
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'errors' in data
    
    def test_invalid_booking_cancellation(self, client, admin_token, app):
        """Test booking cancellation requires reason"""
        with app.app_context():
            booking = Booking(
                user_id=User.query.first().id,
                booking_type='flight',
                status=BookingStatus.PENDING,
                base_price=100.00,
                service_fee=10.00,
                total_price=110.00
            )
            db.session.add(booking)
            db.session.commit()
            booking_id = booking.id
        
        response = client.post(f'/api/admin/bookings/{booking_id}/cancel',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={}  # Missing reason
        )
        
        assert response.status_code == 422


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
