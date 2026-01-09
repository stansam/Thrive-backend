from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import uuid
from decimal import Decimal
from app.extensions import db
from app.models.enums import BookingStatus, TripType, TravelClass

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_reference = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # User info
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Booking type
    booking_type = db.Column(db.String(20), nullable=False)  # flight, package, hotel, custom
    status = db.Column(db.Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    
    # Trip details
    trip_type = db.Column(db.Enum(TripType))
    origin = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    departure_date = db.Column(db.DateTime)
    return_date = db.Column(db.DateTime)
    
    # Flight specific
    airline = db.Column(db.String(100))
    flight_number = db.Column(db.String(20))
    flight_offer = db.Column(db.JSON)  # Raw Amadeus offer object
    travel_class = db.Column(db.Enum(TravelClass))
    num_adults = db.Column(db.Integer, default=1)
    num_children = db.Column(db.Integer, default=0)
    num_infants = db.Column(db.Integer, default=0)
    
    # Package tour (if applicable)
    package_id = db.Column(db.String(36), db.ForeignKey('packages.id'))
    
    # Pricing
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    service_fee = db.Column(db.Numeric(10, 2), nullable=False)
    taxes = db.Column(db.Numeric(10, 2), default=0.00)
    discount = db.Column(db.Numeric(10, 2), default=0.00)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Additional details
    is_urgent = db.Column(db.Boolean, default=False)
    special_requests = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Confirmations
    airline_confirmation = db.Column(db.String(50))
    ticket_numbers = db.Column(db.JSON)  # List of ticket numbers
    
    # Agent handling
    assigned_agent_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    confirmed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Relationships
    passengers = db.relationship('Passenger', backref='booking', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='booking', lazy='dynamic', cascade='all, delete-orphan')
    agent = db.relationship('User', foreign_keys=[assigned_agent_id], backref='handled_bookings')
    
    def __init__(self, **kwargs):
        super(Booking, self).__init__(**kwargs)
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
    
    @staticmethod
    def generate_booking_reference():
        """Generate unique booking reference like TGT-ABC123"""
        import random
        import string
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        numbers = ''.join(random.choices(string.digits, k=3))
        return f"TGT-{letters}{numbers}"
    
    def calculate_total(self):
        """Calculate total booking price"""
        self.total_price = (self.base_price + self.service_fee + 
                           self.taxes - self.discount)
        return self.total_price
    
    def get_total_passengers(self):
        return self.num_adults + self.num_children + self.num_infants
    
    def to_dict(self):
        return {
            'id': self.id,
            'booking_reference': self.booking_reference,
            'booking_type': self.booking_type,
            'status': self.status.value,
            'origin': self.origin,
            'destination': self.destination,
            'departure_date': self.departure_date.isoformat() if self.departure_date else None,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'total_price': float(self.total_price),
            'created_at': self.created_at.isoformat()
        }
