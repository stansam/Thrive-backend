"""
Database Initialization Script
Creates tables and initializes the database with sample data for testing
"""

from app.extensions import db
from app.models import User, Booking, Package, Payment, Notification, Settings
from app.models.enums import UserRole, SubscriptionTier, BookingStatus, PaymentStatus
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
import random


def clear_database():
    """Drop all tables and recreate them"""
    print("🗑️  Dropping all tables...")
    db.drop_all()
    print("✅ Tables dropped successfully")
    
    print("📋 Creating tables...")
    db.create_all()
    print("✅ Tables created successfully")


def init_database(with_sample_data=True):
    """
    Initialize the database with tables and optionally sample data
    
    Args:
        with_sample_data (bool): Whether to populate with sample data
    """
    print("🚀 Initializing database...")
    
    # Create tables
    print("📋 Creating tables...")
    db.create_all()
    print("✅ Tables created successfully")
    
    if with_sample_data:
        print("\n📦 Creating sample data...")
        from .sample_data import (
            create_sample_users,
            # create_sample_packages,
            create_sample_bookings,
            create_sample_payments,
            create_sample_notifications,
            create_sample_settings
        )
        
        # Create data in order (respecting foreign keys)
        users = create_sample_users()
        packages = Package.query.order_by(Package.id.asc()).all()
        bookings = create_sample_bookings(users, packages)
        payments = create_sample_payments(users, bookings)
        notifications = create_sample_notifications(users, bookings)
        settings = create_sample_settings()
        
        print(f"\n✅ Database initialized successfully!")
        print(f"   - Users: {len(users)}")
        print(f"   - Packages: {len(packages)}")
        print(f"   - Bookings: {len(bookings)}")
        print(f"   - Payments: {len(payments)}")
        print(f"   - Notifications: {len(notifications)}")
        print(f"   - Settings: {len(settings)}")
        
        # Print test user credentials
        print("\n🔑 Test User Credentials:")
        print("   Email: john.doe@example.com")
        print("   Password: password123")
        print("\n   Email: jane.smith@example.com")
        print("   Password: password123")
        print("\n   Email: admin@thrivetravel.com")
        print("   Password: admin123")
    else:
        print("✅ Database tables created (no sample data)")
    
    return True


def reset_database():
    """Complete database reset - drop, create, and populate"""
    print("⚠️  RESETTING DATABASE - This will delete all data!")
    clear_database()
    init_database(with_sample_data=True)
    print("\n✅ Database reset complete!")
