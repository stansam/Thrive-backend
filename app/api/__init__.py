# Routes package
from flask import Blueprint

api_bp = Blueprint('api', __name__)

from app.api.main import routes
from app.api.admin import routes 
from app.api.auth import routes
from app.api.client import routes