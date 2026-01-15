from flask import jsonify, request, current_app
from datetime import datetime, timezone
import logging

from app.api.payments import payment_bp as bp
from app.models.payment import Payment
from app.models.enums import BookingStatus, PaymentStatus
from app.services.payment import PaymentService
from app.extensions import db

logger = logging.getLogger(__name__)

# ==================== WEBHOOK ENDPOINT ====================

@bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events
    
    This endpoint receives notifications from Stripe about payment events
    """
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    if not sig_header:
        return jsonify({'error': 'Missing signature'}), 400
    
    try:
        payment_service = PaymentService(current_app.config)
        event_data = payment_service.handle_webhook(payload, sig_header)
        
        event_type = event_data.get('event_type')
        
        # Handle different event types
        if event_type == 'payment_succeeded':
            payment_intent_id = event_data.get('payment_intent_id')
            
            # Find payment and update status
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            
            if payment and payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.PAID
                payment.paid_at = datetime.now(timezone.utc)
                
                # Update booking
                if payment.booking:
                    payment.booking.status = BookingStatus.CONFIRMED
                    payment.booking.confirmed_at = datetime.now(timezone.utc)
                
                db.session.commit()
                
                logger.info(f"Webhook: Payment succeeded for {payment_intent_id}")
        
        elif event_type == 'payment_failed':
            payment_intent_id = event_data.get('payment_intent_id')
            
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            
            if payment:
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = event_data.get('error', 'Payment failed')
                db.session.commit()
                
                logger.warning(f"Webhook: Payment failed for {payment_intent_id}")
        
        elif event_type == 'refund_processed':
            # Handle refund notification
            logger.info(f"Webhook: Refund processed")
        
        return jsonify({'received': True}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 400
