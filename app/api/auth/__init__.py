"""
Authentication API module
"""
from flask import Blueprint

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

from app.api.auth import access, registration, password, profile

__all__ = ['auth_bp']
