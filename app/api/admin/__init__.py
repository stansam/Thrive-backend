"""
Admin API Blueprint
Handles all admin panel functionalities
"""
from flask import Blueprint

# Create admin blueprint with /api/admin prefix
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Import routes after blueprint creation to avoid circular imports
from . import dashboard, users, bookings, quotes, packages, payments, contacts
