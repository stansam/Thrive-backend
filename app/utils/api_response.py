from flask import jsonify, current_app
from functools import wraps
from flask_login import current_user
from datetime import datetime, timedelta
from decimal import Decimal
import random
import string
import re
from typing import Dict, List, Optional, Tuple
import requests

class APIResponse:
    """Standardized API response format"""
    
    @staticmethod
    def success(data=None, message=None, status_code=200):
        """Success response"""
        response = {
            'success': True,
            'message': message or 'Operation successful'
        }
        if data is not None:
            response['data'] = data
        return jsonify(response), status_code
    
    @staticmethod
    def error(message, errors=None, status_code=400):
        """Error response"""
        response = {
            'success': False,
            'message': message
        }
        if errors:
            response['errors'] = errors
        return jsonify(response), status_code
    
    @staticmethod
    def validation_error(errors, message="Validation failed"):
        """Validation error response"""
        return APIResponse.error(message, errors=errors, status_code=422)
    
    @staticmethod
    def unauthorized(message="Unauthorized access"):
        """Unauthorized response"""
        return APIResponse.error(message, status_code=401)
    
    @staticmethod
    def forbidden(message="Forbidden"):
        """Forbidden response"""
        return APIResponse.error(message, status_code=403)
    
    @staticmethod
    def not_found(message="Resource not found"):
        """Not found response"""
        return APIResponse.error(message, status_code=404)