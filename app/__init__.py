from flask import Flask
from app.extensions import db, migrate
from flask_cors import CORS
from config import Config



def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app) # Enable CORS for all routes

    # Register Blueprint
    from app.api import api_bp
    app.register_blueprint(api_bp)


    return app
