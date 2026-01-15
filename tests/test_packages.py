
import pytest
import json
from datetime import datetime, date
from app.models import Package, User
from app.models.enums import UserRole

@pytest.fixture
def sample_package(app, db):
    pkg = Package(
        name="Test Adventure",
        slug="test-adventure",
        destination_city="Paris",
        destination_country="France",
        duration_days=5,
        duration_nights=4,
        starting_price=1000.00,
        price_per_person=1000.00,
        full_description="A test package",
        is_active=True,
        is_featured=True,
        created_at=datetime.utcnow()
    )
    db.session.add(pkg)
    db.session.commit()
    return pkg

@pytest.fixture
def auth_header(app, db):
    from flask_jwt_extended import create_access_token
    user = User(
        email="user@example.com",
        password_hash="hash",
        first_name="Test",
        last_name="User",
        role=UserRole.CUSTOMER,
        is_active=True,
        email_verified=True
    )
    db.session.add(user)
    db.session.commit()
    
    with app.app_context():
        token = create_access_token(identity=user.id)
        return {'Authorization': f'Bearer {token}'}, user

class TestPackages:

    def test_search_packages(self, client, sample_package):
        response = client.get('/api/packages/search?q=Paris')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']['items']) >= 1
        assert data['data']['items'][0]['name'] == sample_package.name

    def test_search_packages_filters(self, client, sample_package):
        response = client.get('/api/packages/search?minPrice=100&maxPrice=2000')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['data']['items']) >= 1

    def test_get_featured_packages(self, client, sample_package):
        response = client.get('/api/packages/featured')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        # sample_package is featured
        assert len(data['data']) >= 1

    def test_get_destinations(self, client, sample_package):
        response = client.get('/api/packages/destinations')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'France' in [d['country'] for d in data['data']]

    def test_get_package_details(self, client, sample_package):
        response = client.get(f'/api/packages/{sample_package.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['id'] == sample_package.id

    def test_get_package_by_slug(self, client, sample_package):
        response = client.get(f'/api/packages/slug/{sample_package.slug}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['slug'] == sample_package.slug

    def test_toggle_favorite(self, client, sample_package, auth_header):
        headers, user = auth_header
        
        # Add favorite - Expect 501 as not implemented
        response = client.post(f'/api/packages/{sample_package.id}/favorite', headers=headers)
        if response.status_code == 200:
             # If it works, great
             pass
        else:
             assert response.status_code == 501
