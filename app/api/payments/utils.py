from functools import wraps
from flask import jsonify, request
import logging
from app.extensions import db
from app.models.audit_log import AuditLog
from app.services.payment import PaymentServiceError

logger = logging.getLogger(__name__)

def handle_payment_error(f):
    """Decorator for consistent payment error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except PaymentServiceError as e:
            logger.error(f"Payment service error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'PAYMENT_ERROR',
                'message': str(e)
            }), 400
        except Exception as e:
            logger.exception("Unexpected error in payment endpoint")
            return jsonify({
                'success': False,
                'error': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred. Please try again.'
            }), 500
    return decorated_function


def log_audit(user_id, action, entity_type, entity_id, description):
    """Helper to log audit entries"""
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {str(e)}")
