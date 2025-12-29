from datetime import datetime
import uuid
from decimal import Decimal
from app.extensions import db
from app.models.enums import PaymentStatus

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Links
    booking_id = db.Column(db.String(36), db.ForeignKey('bookings.id'), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Payment details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    payment_method = db.Column(db.String(50))  # card, stripe, paypal, bank_transfer
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Stripe/Payment gateway
    stripe_payment_intent_id = db.Column(db.String(100))
    stripe_charge_id = db.Column(db.String(100))
    transaction_id = db.Column(db.String(100))
    
    # Card info (last 4 digits only)
    card_last4 = db.Column(db.String(4))
    card_brand = db.Column(db.String(20))
    
    # Metadata
    payment_metadata = db.Column(db.JSON)
    failure_reason = db.Column(db.Text)
    
    # Refund info
    refund_amount = db.Column(db.Numeric(10, 2), default=0.00)
    refund_reason = db.Column(db.Text)
    refunded_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    paid_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'payment_reference': self.payment_reference,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status.value,
            'payment_method': self.payment_method,
            'created_at': self.created_at.isoformat()
        }