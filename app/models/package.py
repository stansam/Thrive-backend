from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import uuid
from app.extensions import db

class Package(db.Model):
    __tablename__ = 'packages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Destination
    destination_city = db.Column(db.String(100), nullable=False)
    destination_country = db.Column(db.String(100), nullable=False)
    
    # Duration
    duration_days = db.Column(db.Integer, nullable=False)
    duration_nights = db.Column(db.Integer, nullable=False)
    
    # Pricing
    starting_price = db.Column(db.Numeric(10, 2), nullable=False)
    price_per_person = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Package details
    highlights = db.Column(db.JSON)  # List of highlights
    inclusions = db.Column(db.JSON)  # List of what's included
    exclusions = db.Column(db.JSON)  # List of what's not included
    itinerary = db.Column(db.JSON)  # Day-by-day itinerary
    
    # Accommodation
    hotel_name = db.Column(db.String(200))
    hotel_rating = db.Column(db.Integer)
    room_type = db.Column(db.String(100))
    
    # Availability
    is_active = db.Column(db.Boolean, default=True)
    available_from = db.Column(db.Date)
    available_until = db.Column(db.Date)
    max_capacity = db.Column(db.Integer)
    min_booking = db.Column(db.Integer, default=1)
    
    # Media
    featured_image = db.Column(db.String(500))
    gallery_images = db.Column(db.JSON)  # List of image URLs
    
    # SEO
    meta_title = db.Column(db.String(200))
    meta_description = db.Column(db.Text)
    
    # Stats
    view_count = db.Column(db.Integer, default=0)
    booking_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bookings = db.relationship('Booking', backref='package', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'destination': f"{self.destination_city}, {self.destination_country}",
            'duration': f"{self.duration_days} Days / {self.duration_nights} Nights",
            'starting_price': float(self.starting_price),
            'highlights': self.highlights,
            'inclusions': self.inclusions,
            'exclusions': self.exclusions,
            'featured_image': self.featured_image,
            'is_active': self.is_active
        }
