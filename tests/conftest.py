import pytest
from app import create_app
from app.extensions import db as _db
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    # API Keys for testing
    AMADEUS_API_KEY = "test_key"
    AMADEUS_SECRET_KEY = "test_secret"
    STRIPE_SECRET_KEY = "sk_test_123"
    STRIPE_PUBLISHABLE_KEY = "pk_test_123"

@pytest.fixture
def app():
    app = create_app(TestConfig)
    
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def db(app):
    return _db
