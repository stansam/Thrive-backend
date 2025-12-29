from flask import jsonify, current_app
from functools import wraps
from flask_login import current_user
from datetime import datetime, timedelta
import string
from typing import Dict, List, Optional, Tuple
from app.utils.api_response import APIResponse

def role_required(*roles):
    """Decorator to require specific user roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return APIResponse.unauthorized("Please login to continue")
            
            if current_user.role.value not in roles:
                return APIResponse.forbidden("You don't have permission to access this resource")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def subscription_required(*tiers):
    """Decorator to require specific subscription tiers"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return APIResponse.unauthorized("Please login to continue")
            
            if not current_user.has_active_subscription():
                return APIResponse.forbidden("Active subscription required")
            
            if tiers and current_user.subscription_tier.value not in tiers:
                return APIResponse.forbidden(f"Subscription tier {' or '.join(tiers)} required")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator