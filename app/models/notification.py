from datetime import datetime, timezone
import uuid
from app.extensions import db

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Notification details
    type = db.Column(db.String(50), nullable=False)  # booking_confirmed, payment_received, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Links
    link_url = db.Column(db.String(500))
    booking_id = db.Column(db.String(36), db.ForeignKey('bookings.id'))
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # Delivery
    sent_via_email = db.Column(db.Boolean, default=False)
    sent_via_sms = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }
