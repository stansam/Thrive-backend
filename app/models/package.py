from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone, date
import uuid
from app.extensions import db
from slugify import slugify  # pip install python-slugify

class Package(db.Model):
    __tablename__ = 'packages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    short_description = db.Column(db.Text)
    full_description = db.Column(db.Text)
    
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
    highlights = db.Column(db.JSON)
    inclusions = db.Column(db.JSON)
    exclusions = db.Column(db.JSON)
    itinerary = db.Column(db.JSON)
    
    # Accommodation
    hotel_name = db.Column(db.String(200))
    hotel_rating = db.Column(db.Integer)
    hotel_address = db.Column(db.String(200))
    hotel_phone = db.Column(db.String(20))
    room_type = db.Column(db.String(100))
    
    # Availability
    is_active = db.Column(db.Boolean, default=True)
    available_from = db.Column(db.Date)
    available_until = db.Column(db.Date)
    max_capacity = db.Column(db.Integer)
    min_booking = db.Column(db.Integer, default=1)

    # Marketing
    is_featured = db.Column(db.Boolean, default=False)
    marketing_tagline = db.Column(db.String(500))

    # Media
    featured_image = db.Column(db.String(500))
    gallery_images = db.Column(db.JSON)
    
    # SEO
    meta_title = db.Column(db.String(200))
    meta_description = db.Column(db.Text)
    
    # Stats
    view_count = db.Column(db.Integer, default=0)
    booking_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    bookings = db.relationship('Booking', backref='package', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'short_description': self.short_description,
            'full_description': self.full_description,
            'destination_city': self.destination_city,
            'destination_country': self.destination_country,
            'duration_days': self.duration_days,
            'duration_nights': self.duration_nights,
            'starting_price': float(self.starting_price),
            'price_per_person': float(self.price_per_person),
            'highlights': self.highlights,
            'inclusions': self.inclusions,
            'exclusions': self.exclusions,
            'itinerary': self.itinerary,
            'hotel_name': self.hotel_name if self.hotel_name else None,
            'hotel_rating': self.hotel_rating if self.hotel_rating else None,
            'hotel_address': self.hotel_address if self.hotel_address else None,
            'hotel_phone': self.hotel_phone if self.hotel_phone else None,
            'room_type': self.room_type if self.room_type else None,
            'is_active': self.is_active,
            'available_from': self.available_from if self.available_from else None,
            'available_until': self.available_until if self.available_until else None,
            'max_capacity': self.max_capacity if self.max_capacity else None,
            'min_booking': self.min_booking if self.min_booking else None,
            'is_featured': self.is_featured,
            'marketing_tagline': self.marketing_tagline if self.marketing_tagline else None,
            'featured_image': self.featured_image if self.featured_image else None,
            'gallery_images': self.gallery_images if self.gallery_images else None,
            'meta_title': self.meta_title if self.meta_title else None,
            'meta_description': self.meta_description if self.meta_description else None,
            'view_count': self.view_count,
            'booking_count': self.booking_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def load_packages(packages_data, clear_existing=False):
        """
        Load packages from sample data into the database.
        
        Args:
            packages_data: List of dictionaries containing package information
            clear_existing: If True, clear all existing packages before loading
            
        Returns:
            tuple: (success_count, error_count, errors_list)
        """
        success_count = 0
        error_count = 0
        errors = []
        
        try:
            # Clear existing packages if requested
            if clear_existing:
                Package.query.delete()
                db.session.commit()
                print("Cleared existing packages.")
            
            # Load each package
            for idx, package_data in enumerate(packages_data, 1):
                try:
                    # Generate slug if not provided
                    if 'slug' not in package_data or not package_data['slug']:
                        package_data['slug'] = slugify(package_data['name'])
                    
                    # Check if package with this slug already exists
                    existing = Package.query.filter_by(slug=package_data['slug']).first()
                    if existing:
                        print(f"Package '{package_data['name']}' already exists. Skipping...")
                        continue
                    
                    # Convert date strings to date objects if present
                    if 'available_from' in package_data and isinstance(package_data['available_from'], str):
                        package_data['available_from'] = datetime.strptime(
                            package_data['available_from'], '%Y-%m-%d'
                        ).date()
                    
                    if 'available_until' in package_data and isinstance(package_data['available_until'], str):
                        package_data['available_until'] = datetime.strptime(
                            package_data['available_until'], '%Y-%m-%d'
                        ).date()
                    
                    # Create new package
                    package = Package(**package_data)
                    db.session.add(package)
                    db.session.commit()
                    
                    success_count += 1
                    print(f"✓ Loaded package {idx}/{len(packages_data)}: {package.name}")
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"Error loading package {idx}: {str(e)}"
                    errors.append(error_msg)
                    print(f"✗ {error_msg}")
                    db.session.rollback()
            
            print(f"\n{'='*50}")
            print(f"Package loading complete!")
            print(f"Successfully loaded: {success_count}")
            print(f"Errors: {error_count}")
            print(f"{'='*50}\n")
            
            return success_count, error_count, errors
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Critical error during package loading: {str(e)}"
            print(f"✗ {error_msg}")
            return success_count, error_count, [error_msg]