from datetime import datetime
from app import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    bookings = db.relationship('Booking', backref='user', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': self.created_at.isoformat(),
            'is_admin': self.is_admin
        }

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    booking_reference = db.Column(db.String(10), unique=True, nullable=False) # PNR
    total_price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.String(20), default='confirmed') # confirmed, pending, cancelled
    flight_snapshot = db.Column(db.JSON, nullable=True) # Stores flight details
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    travelers = db.relationship('Traveler', backref='booking', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'booking_reference': self.booking_reference,
            'total_price': self.total_price,
            'currency': self.currency,
            'status': self.status,
            'flight_snapshot': self.flight_snapshot,
            'created_at': self.created_at.isoformat(),
            'travelers': [t.to_dict() for t in self.travelers]
        }

class Traveler(db.Model):
    __tablename__ = 'travelers'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20))
    passport_number = db.Column(db.String(50))
    passport_expiry = db.Column(db.Date)
    nationality = db.Column(db.String(3))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'passport_number': self.passport_number,
            'passport_expiry': self.passport_expiry.isoformat() if self.passport_expiry else None,
            'nationality': self.nationality,
            'email': self.email,
            'phone': self.phone
        }

class SearchHistory(db.Model):
    __tablename__ = 'search_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    origin = db.Column(db.String(10), nullable=False)
    destination = db.Column(db.String(10), nullable=False)
    departure_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'origin': self.origin,
            'destination': self.destination,
            'departure_date': self.departure_date.isoformat(),
            'created_at': self.created_at.isoformat()
        }
