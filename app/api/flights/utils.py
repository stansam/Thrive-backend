from functools import wraps
from flask import jsonify, current_app, request
import logging
from app.extensions import db
from app.models.audit_log import AuditLog
from app.services.amadeus import (
    AmadeusAPIError, ValidationError, BookingError, RateLimitError,
    TravelClass as AmadeusTravelClass
)

logger = logging.getLogger(__name__)

def handle_api_error(f):
    """Decorator for consistent error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error: {e.message}")
            return jsonify({
                'success': False,
                'error': 'VALIDATION_ERROR',
                'message': e.message,
                'details': e.response
            }), 400
        except RateLimitError as e:
            logger.warning("Rate limit exceeded")
            return jsonify({
                'success': False,
                'error': 'RATE_LIMIT_EXCEEDED',
                'message': 'Too many requests. Please try again later.',
                'retry_after': 60
            }), 429
        except BookingError as e:
            logger.error(f"Booking error: {e.message}")
            return jsonify({
                'success': False,
                'error': 'BOOKING_ERROR',
                'message': e.message,
                'details': e.response
            }), 400
        except AmadeusAPIError as e:
            logger.error(f"Amadeus API error: {e.message}")
            return jsonify({
                'success': False,
                'error': 'API_ERROR',
                'message': 'Unable to process your request. Please try again.',
                'technical_details': e.message if current_app.debug else None
            }), 500
        except Exception as e:
            logger.exception("Unexpected error in API endpoint")
            return jsonify({
                'success': False,
                'error': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred. Please try again later.'
            }), 500
    return decorated_function


def log_audit(user_id, action, entity_type, entity_id, description, changes=None):
    """Helper to log audit entries"""
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            changes=changes,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {str(e)}")


def map_travel_class(frontend_class: str) -> AmadeusTravelClass:
    """Map frontend travel class to Amadeus enum"""
    mapping = {
        'ECONOMY': AmadeusTravelClass.ECONOMY,
        'PREMIUM_ECONOMY': AmadeusTravelClass.PREMIUM_ECONOMY,
        'BUSINESS': AmadeusTravelClass.BUSINESS,
        'FIRST': AmadeusTravelClass.FIRST
    }
    return mapping.get(frontend_class.upper(), AmadeusTravelClass.ECONOMY)
