
from flask import Blueprint

client_bp = Blueprint('client', __name__, url_prefix='/api/client/dashboard')

from . import dashboard, profile, subscriptions, bookings, flights, packages
