"""
Comprehensive tests for authentication API endpoints
Run with: pytest tests/test_auth.py -v
"""
import pytest
import json
from datetime import datetime
from app import create_app, db
from app.models import User
from app.models.enums import UserRole, SubscriptionTier
from config import Config


class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'
    GOOGLE_CLIENT_ID = 'test-google-client-id'


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
            role=UserRole.CUSTOMER,
            subscription_tier=SubscriptionTier.NONE,
            email_verified=True,
            is_active=True
        )
        user.set_password('TestPass123')
        user.referral_code = 'TEST123456'
        
        db.session.add(user)
        db.session.commit()
        
        return user


class TestUserRegistration:
    """Test user registration endpoint"""
    
    def test_successful_registration(self, client):
        """Test successful user registration"""
        response = client.post('/api/auth/register', json={
            'fullName': 'John Doe',
            'email': 'john@example.com',
            'password': 'SecurePass123',
            'confirmPassword': 'SecurePass123'
        })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'user' in data['data']
        assert 'tokens' in data['data']
        assert data['data']['user']['email'] == 'john@example.com'
        assert data['data']['user']['first_name'] == 'John'
        assert data['data']['user']['last_name'] == 'Doe'
        assert 'accessToken' in data['data']['tokens']
        assert 'refreshToken' in data['data']['tokens']
    
    def test_registration_with_phone(self, client):
        """Test registration with optional phone number"""
        response = client.post('/api/auth/register', json={
            'fullName': 'Jane Smith',
            'email': 'jane@example.com',
            'password': 'SecurePass123',
            'confirmPassword': 'SecurePass123',
            'phone': '+1234567890'
        })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['data']['user']['phone'] == '+1234567890'
    
    def test_registration_with_referral_code(self, client, sample_user):
        """Test registration with valid referral code"""
        response = client.post('/api/auth/register', json={
            'fullName': 'Bob Johnson',
            'email': 'bob@example.com',
            'password': 'SecurePass123',
            'confirmPassword': 'SecurePass123',
            'referralCode': 'TEST123456'
        })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_registration_duplicate_email(self, client, sample_user):
        """Test registration with existing email"""
        response = client.post('/api/auth/register', json={
            'fullName': 'Test User',
            'email': 'test@example.com',
            'password': 'SecurePass123',
            'confirmPassword': 'SecurePass123'
        })
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'already registered' in data['message'].lower()
    
    def test_registration_invalid_email(self, client):
        """Test registration with invalid email format"""
        response = client.post('/api/auth/register', json={
            'fullName': 'Test User',
            'email': 'invalid-email',
            'password': 'SecurePass123',
            'confirmPassword': 'SecurePass123'
        })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'email' in data['errors']
    
    def test_registration_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post('/api/auth/register', json={
            'fullName': 'Test User',
            'email': 'test2@example.com',
            'password': 'weak',
            'confirmPassword': 'weak'
        })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'password' in data['errors']
    
    def test_registration_password_mismatch(self, client):
        """Test registration with mismatched passwords"""
        response = client.post('/api/auth/register', json={
            'fullName': 'Test User',
            'email': 'test3@example.com',
            'password': 'SecurePass123',
            'confirmPassword': 'DifferentPass123'
        })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'confirmPassword' in data['errors']
    
    def test_registration_missing_fields(self, client):
        """Test registration with missing required fields"""
        response = client.post('/api/auth/register', json={
            'email': 'test4@example.com'
        })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'fullName' in data['errors']
        assert 'password' in data['errors']
    
    def test_registration_invalid_referral_code(self, client):
        """Test registration with invalid referral code"""
        response = client.post('/api/auth/register', json={
            'fullName': 'Test User',
            'email': 'test5@example.com',
            'password': 'SecurePass123',
            'confirmPassword': 'SecurePass123',
            'referralCode': 'INVALID123'
        })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'referralCode' in data['errors']


class TestUserLogin:
    """Test user login endpoint"""
    
    def test_successful_login(self, client, sample_user):
        """Test successful login"""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'user' in data['data']
        assert 'tokens' in data['data']
        assert data['data']['user']['email'] == 'test@example.com'
    
    def test_login_with_remember_me(self, client, sample_user):
        """Test login with remember me flag"""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123',
            'rememberMe': True
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_login_invalid_email(self, client):
        """Test login with non-existent email"""
        response = client.post('/api/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'SomePass123'
        })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_login_invalid_password(self, client, sample_user):
        """Test login with wrong password"""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'WrongPass123'
        })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_login_missing_fields(self, client):
        """Test login with missing fields"""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com'
        })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'password' in data['errors']


class TestTokenRefresh:
    """Test token refresh endpoint"""
    
    def test_successful_token_refresh(self, client, sample_user):
        """Test successful token refresh"""
        # First login to get tokens
        login_response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123'
        })
        login_data = json.loads(login_response.data)
        refresh_token = login_data['data']['tokens']['refreshToken']
        
        # Refresh token
        response = client.post('/api/auth/refresh',
            headers={'Authorization': f'Bearer {refresh_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'tokens' in data['data']
        assert 'accessToken' in data['data']['tokens']
    
    def test_token_refresh_without_token(self, client):
        """Test token refresh without providing token"""
        response = client.post('/api/auth/refresh')
        
        assert response.status_code == 401


class TestLogout:
    """Test logout endpoint"""
    
    def test_successful_logout(self, client, sample_user):
        """Test successful logout"""
        # First login
        login_response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123'
        })
        login_data = json.loads(login_response.data)
        access_token = login_data['data']['tokens']['accessToken']
        
        # Logout
        response = client.post('/api/auth/logout',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestPasswordReset:
    """Test password reset endpoints"""
    
    def test_password_reset_request(self, client, sample_user):
        """Test password reset request"""
        response = client.post('/api/auth/password-reset/request', json={
            'email': 'test@example.com'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_password_reset_request_nonexistent_email(self, client):
        """Test password reset request with non-existent email"""
        response = client.post('/api/auth/password-reset/request', json={
            'email': 'nonexistent@example.com'
        })
        
        # Should still return success for security
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_password_reset_request_invalid_email(self, client):
        """Test password reset request with invalid email"""
        response = client.post('/api/auth/password-reset/request', json={
            'email': 'invalid-email'
        })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'email' in data['errors']


class TestGetCurrentUser:
    """Test get current user endpoint"""
    
    def test_get_current_user(self, client, sample_user):
        """Test getting current user"""
        # First login
        login_response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123'
        })
        login_data = json.loads(login_response.data)
        access_token = login_data['data']['tokens']['accessToken']
        
        # Get current user
        response = client.get('/api/auth/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['user']['email'] == 'test@example.com'
    
    def test_get_current_user_without_token(self, client):
        """Test getting current user without token"""
        response = client.get('/api/auth/me')
        
        assert response.status_code == 401


class TestValidationSchemas:
    """Test validation schema edge cases"""
    
    def test_name_splitting(self, client):
        """Test full name splitting into first and last name"""
        # Single name
        response = client.post('/api/auth/register', json={
            'fullName': 'Madonna',
            'email': 'madonna@example.com',
            'password': 'SecurePass123',
            'confirmPassword': 'SecurePass123'
        })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['data']['user']['first_name'] == 'Madonna'
        assert data['data']['user']['last_name'] == 'Madonna'
    
    def test_multiple_names(self, client):
        """Test full name with multiple parts"""
        response = client.post('/api/auth/register', json={
            'fullName': 'John Paul Smith Jr.',
            'email': 'jpsmith@example.com',
            'password': 'SecurePass123',
            'confirmPassword': 'SecurePass123'
        })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['data']['user']['first_name'] == 'John'
        assert data['data']['user']['last_name'] == 'Paul Smith Jr.'
    
    def test_email_case_insensitive(self, client, sample_user):
        """Test email is case-insensitive"""
        response = client.post('/api/auth/login', json={
            'email': 'TEST@EXAMPLE.COM',
            'password': 'TestPass123'
        })
        
        assert response.status_code == 200
    
    def test_password_strength_validation(self, client):
        """Test password strength requirements"""
        # Only letters
        response = client.post('/api/auth/register', json={
            'fullName': 'Test User',
            'email': 'test1@example.com',
            'password': 'onlyletters',
            'confirmPassword': 'onlyletters'
        })
        assert response.status_code == 422
        
        # Only numbers
        response = client.post('/api/auth/register', json={
            'fullName': 'Test User',
            'email': 'test2@example.com',
            'password': '12345678',
            'confirmPassword': '12345678'
        })
        assert response.status_code == 422


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
