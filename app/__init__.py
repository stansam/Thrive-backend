from flask import Flask
from app.extensions import db, migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config



def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)  # Enable CORS for all routes
    
    # Initialize JWT
    jwt = JWTManager(app)

    # Register Blueprints
    from app.api import api_bp
    from app.api.auth import auth_bp
    from app.api.client import client_bp
    
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp)


    return app
