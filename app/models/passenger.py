from datetime import datetime, timezone
import uuid
from app.extensions import db

class Passenger(db.Model):
    __tablename__ = 'passengers'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = db.Column(db.String(36), db.ForeignKey('bookings.id'), nullable=False, index=True)
    
    # Personal info
    title = db.Column(db.String(10))  # Mr, Mrs, Ms, Dr
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10))
    nationality = db.Column(db.String(50))
    
    # Document info
    passport_number = db.Column(db.String(50))
    passport_expiry = db.Column(db.Date)
    passport_country = db.Column(db.String(50))
    
    # Travel info
    passenger_type = db.Column(db.String(20))  # adult, child, infant
    ticket_number = db.Column(db.String(50))
    seat_number = db.Column(db.String(10))
    frequent_flyer_number = db.Column(db.String(50))
    
    # Special requirements
    meal_preference = db.Column(db.String(50))
    special_assistance = db.Column(db.String(200))
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'passenger_type': self.passenger_type,
            'ticket_number': self.ticket_number
        }
