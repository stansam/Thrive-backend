from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import uuid
from app.extensions import db
from app.models.enums import UserRole, SubscriptionTier

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    
    # Profile
    date_of_birth = db.Column(db.Date)
    passport_number = db.Column(db.String(50))
    passport_expiry = db.Column(db.Date)
    nationality = db.Column(db.String(50))
    
    # Preferences
    preferred_airline = db.Column(db.String(100))
    frequent_flyer_numbers = db.Column(db.JSON)  # {"airline": "number"}
    dietary_preferences = db.Column(db.String(200))
    special_assistance = db.Column(db.Text)
    
    # Subscription
    subscription_tier = db.Column(db.Enum(SubscriptionTier), default=SubscriptionTier.NONE)
    subscription_start = db.Column(db.DateTime)
    subscription_end = db.Column(db.DateTime)
    monthly_bookings_used = db.Column(db.Integer, default=0)
    
    # Business info (for corporate users)
    company_name = db.Column(db.String(200))
    company_tax_id = db.Column(db.String(50))
    billing_address = db.Column(db.Text)
    
    # Custom Settings (Notifications, Privacy, etc.)
    custom_settings = db.Column(db.JSON, default={})
    
    # Account status
    email_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    referral_code = db.Column(db.String(20), unique=True, index=True)
    referred_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    referral_credits = db.Column(db.Numeric(10, 2), default=0.00)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    
    # Relationships
    bookings = db.relationship('Booking', backref='customer', lazy='dynamic', foreign_keys='Booking.user_id')
    quotes = db.relationship('Quote', backref='user', lazy='dynamic', foreign_keys='Quote.user_id')
    payments = db.relationship('Payment', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    referrals = db.relationship('User', backref=db.backref('referrer', remote_side=[id]))

    # Favorites
    favorite_packages = db.relationship(
        'Package', 
        secondary='user_favorites', 
        backref=db.backref('favorited_by', lazy='dynamic'), 
        lazy='dynamic'
    )

    # Association table for favorites
    user_favorites = db.Table('user_favorites',
        db.Column('user_id', db.String(36), db.ForeignKey('users.id'), primary_key=True),
        db.Column('package_id', db.String(36), db.ForeignKey('packages.id'), primary_key=True),
        db.Column('created_at', db.DateTime, default=datetime.now(timezone.utc))
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def has_active_subscription(self):
        if not self.subscription_end:
            return False
        end = self.subscription_end
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < end
    
    def can_book(self):
        """Check if user can make more bookings based on subscription"""
        if self.subscription_tier == SubscriptionTier.GOLD:
            return True
        elif self.subscription_tier == SubscriptionTier.SILVER:
            return self.monthly_bookings_used < 15
        elif self.subscription_tier == SubscriptionTier.BRONZE:
            return self.monthly_bookings_used < 6
        return True  # No subscription = pay per booking
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'role': self.role.value,
            'subscription_tier': self.subscription_tier.value,
            'referral_code': self.referral_code,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'referral_credits': float(self.referral_credits)
        }

