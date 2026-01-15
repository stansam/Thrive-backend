from flask import Blueprint
from flask_cors import CORS

flights_bp = Blueprint('flights', __name__, url_prefix='/api/flights')
CORS(flights_bp)

from . import search, pricing, booking, management