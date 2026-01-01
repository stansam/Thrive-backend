from datetime import datetime, timezone
import uuid
from app.extensions import db
from app.models.enums import PaymentStatus, TripType, TravelClass


class Quote(db.Model):
    __tablename__ = 'quotes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_reference = db.Column(db.String(20), unique=True, nullable=False)
    
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    flexible_dates = db.Column(db.String(100), nullable=False)
    # return_date = db.Column(db.Date)
    trip_type = db.Column(db.Enum(TripType), nullable=False)
    
    num_adults = db.Column(db.Integer, default=1)
    num_children = db.Column(db.Integer, default=0)
    
    additional_details = db.Column(db.Text)
    
    status = db.Column(db.String(20), default='pending')  # pending, sent, accepted, expired
    quoted_price = db.Column(db.Numeric(10, 2))
    service_fee = db.Column(db.Numeric(10, 2))
    total_price = db.Column(db.Numeric(10, 2))
    
    agent_notes = db.Column(db.Text)
    quote_details = db.Column(db.JSON)  # Flight options, etc.
    
    converted_to_booking_id = db.Column(db.String(36), db.ForeignKey('bookings.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime)
    quoted_at = db.Column(db.DateTime)

    # Foreign Key
    # user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)

    def is_expired(self):
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self):
        return {
            'id': self.id,
            'quote_reference': self.quote_reference,
            'origin': self.origin,
            'destination': self.destination,
            'flexible_dates': self.flexible_dates,
            'trip_type': self.trip_type.value,
            'num_adults': self.num_adults,
            'num_children': self.num_children,
            'additional_details': self.additional_details,
            'status': self.status,
            'total_price': float(self.total_price) if self.total_price else None,
            'created_at': self.created_at.isoformat()
        }
