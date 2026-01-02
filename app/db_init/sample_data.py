"""
Sample Data Generation
Creates realistic sample data for testing and development
"""

from app.extensions import db
from app.models import User, Booking, Package, Payment, Notification, Settings, Passenger
from app.models.enums import (
    UserRole, SubscriptionTier, BookingStatus, PaymentStatus,
    TripType, TravelClass
)
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
import random
import uuid


def create_sample_users():
    """Create sample users with different subscription tiers"""
    print("   Creating users...")
    
    users = []
    
    # Test user 1 - Regular customer with Bronze subscription
    user1 = User(
        id=str(uuid.uuid4()),
        email='john.doe@example.com',
        password_hash=generate_password_hash('password123'),
        first_name='John',
        last_name='Doe',
        phone='+1234567890',
        role=UserRole.CUSTOMER,
        date_of_birth=datetime(1990, 5, 15).date(),
        passport_number='P123456789',
        passport_expiry=(datetime.now() + timedelta(days=1825)).date(),
        nationality='American',
        preferred_airline='Emirates',
        frequent_flyer_numbers={'Emirates': 'EM123456', 'Delta': 'DL789012'},
        dietary_preferences='Vegetarian',
        subscription_tier=SubscriptionTier.BRONZE,
        subscription_start=datetime.now(timezone.utc) - timedelta(days=30),
        subscription_end=datetime.now(timezone.utc) + timedelta(days=335),
        monthly_bookings_used=3,
        email_verified=True,
        is_active=True,
        referral_code='JOHN2024',
        referral_credits=25.00,
        created_at=datetime.now(timezone.utc) - timedelta(days=90)
    )
    users.append(user1)
    
    # Test user 2 - Customer with Silver subscription
    user2 = User(
        id=str(uuid.uuid4()),
        email='jane.smith@example.com',
        password_hash=generate_password_hash('password123'),
        first_name='Jane',
        last_name='Smith',
        phone='+1987654321',
        role=UserRole.CUSTOMER,
        date_of_birth=datetime(1985, 8, 22).date(),
        passport_number='P987654321',
        passport_expiry=(datetime.now() + timedelta(days=2000)).date(),
        nationality='British',
        preferred_airline='British Airways',
        subscription_tier=SubscriptionTier.SILVER,
        subscription_start=datetime.now(timezone.utc) - timedelta(days=60),
        subscription_end=datetime.now(timezone.utc) + timedelta(days=305),
        monthly_bookings_used=8,
        email_verified=True,
        is_active=True,
        referral_code='JANE2024',
        referral_credits=50.00,
        created_at=datetime.now(timezone.utc) - timedelta(days=120)
    )
    users.append(user2)
    
    # Test user 3 - Customer with Gold subscription
    user3 = User(
        id=str(uuid.uuid4()),
        email='mike.johnson@example.com',
        password_hash=generate_password_hash('password123'),
        first_name='Mike',
        last_name='Johnson',
        phone='+1555123456',
        role=UserRole.CUSTOMER,
        date_of_birth=datetime(1988, 3, 10).date(),
        passport_number='P555666777',
        passport_expiry=(datetime.now() + timedelta(days=1500)).date(),
        nationality='Canadian',
        subscription_tier=SubscriptionTier.GOLD,
        subscription_start=datetime.now(timezone.utc) - timedelta(days=15),
        subscription_end=datetime.now(timezone.utc) + timedelta(days=350),
        monthly_bookings_used=12,
        email_verified=True,
        is_active=True,
        referral_code='MIKE2024',
        referral_credits=100.00,
        created_at=datetime.now(timezone.utc) - timedelta(days=45)
    )
    users.append(user3)
    
    # Test user 4 - Customer without subscription
    user4 = User(
        id=str(uuid.uuid4()),
        email='sarah.williams@example.com',
        password_hash=generate_password_hash('password123'),
        first_name='Sarah',
        last_name='Williams',
        phone='+1444555666',
        role=UserRole.CUSTOMER,
        date_of_birth=datetime(1995, 11, 5).date(),
        subscription_tier=SubscriptionTier.NONE,
        email_verified=True,
        is_active=True,
        referral_code='SARAH2024',
        referral_credits=0.00,
        created_at=datetime.now(timezone.utc) - timedelta(days=10)
    )
    users.append(user4)
    
    # Admin user
    admin = User(
        id=str(uuid.uuid4()),
        email='admin@thrivetravel.com',
        password_hash=generate_password_hash('admin123'),
        first_name='Admin',
        last_name='User',
        phone='+1999888777',
        role=UserRole.ADMIN,
        subscription_tier=SubscriptionTier.GOLD,
        email_verified=True,
        is_active=True,
        referral_code='ADMIN2024',
        created_at=datetime.now(timezone.utc) - timedelta(days=365)
    )
    users.append(admin)
    
    db.session.add_all(users)
    db.session.commit()
    
    print(f"   ✅ Created {len(users)} users")
    return users


def create_sample_packages():
    """Create sample travel packages"""
    print("   Creating packages...")
    
    packages = []
    
    # Package 1 - Bali Paradise
    pkg1 = Package(
        id=str(uuid.uuid4()),
        name='Bali Paradise Getaway',
        slug='bali-paradise-getaway',
        description='Experience the magic of Bali with our 7-day all-inclusive package. Explore ancient temples, pristine beaches, and lush rice terraces.',
        destination_city='Bali',
        destination_country='Indonesia',
        duration_days=7,
        duration_nights=6,
        starting_price=1299.00,
        price_per_person=1299.00,
        hotel_name='Grand Hyatt Bali',
        hotel_rating=5,
        room_type='Deluxe Ocean View',
        featured_image='https://images.unsplash.com/photo-1537996194471-e657df975ab4',
        gallery_images=[
            'https://images.unsplash.com/photo-1537996194471-e657df975ab4',
            'https://images.unsplash.com/photo-1559827260-dc66d52bef19',
            'https://images.unsplash.com/photo-1555400038-63f5ba517a47'
        ],
        highlights=[
            'Visit Tanah Lot Temple at sunset',
            'Explore Ubud Rice Terraces',
            'Snorkeling in Nusa Penida',
            'Traditional Balinese massage',
            'Cooking class with local chef'
        ],
        inclusions=[
            'Round-trip flights',
            '6 nights accommodation',
            'Daily breakfast',
            'Airport transfers',
            'Guided tours',
            'Travel insurance'
        ],
        exclusions=[
            'Lunch and dinner',
            'Personal expenses',
            'Optional activities',
            'Visa fees'
        ],
        itinerary=[
            {'day': 1, 'title': 'Arrival', 'description': 'Arrive in Bali, hotel check-in, welcome dinner'},
            {'day': 2, 'title': 'Ubud Tour', 'description': 'Visit rice terraces, monkey forest, and art markets'},
            {'day': 3, 'title': 'Temple Tour', 'description': 'Explore Tanah Lot and Uluwatu temples'},
            {'day': 4, 'title': 'Beach Day', 'description': 'Relax at Seminyak Beach, water sports'},
            {'day': 5, 'title': 'Nusa Penida', 'description': 'Day trip to Nusa Penida island'},
            {'day': 6, 'title': 'Spa & Shopping', 'description': 'Traditional spa treatment, shopping in Kuta'},
            {'day': 7, 'title': 'Departure', 'description': 'Check-out and airport transfer'}
        ],
        is_active=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=60)
    )
    packages.append(pkg1)
    
    # Package 2 - Dubai Luxury
    pkg2 = Package(
        id=str(uuid.uuid4()),
        name='Dubai Luxury Experience',
        slug='dubai-luxury-experience',
        description='Discover the opulence of Dubai with our exclusive 5-day luxury package. From desert safaris to world-class shopping.',
        destination_city='Dubai',
        destination_country='UAE',
        duration_days=5,
        duration_nights=4,
        starting_price=1899.00,
        price_per_person=1899.00,
        hotel_name='Burj Al Arab',
        hotel_rating=5,
        room_type='Deluxe Suite',
        featured_image='https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
        gallery_images=[
            'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
            'https://images.unsplash.com/photo-1518684079-3c830dcef090',
            'https://images.unsplash.com/photo-1580674285054-bed31e145f59'
        ],
        highlights=[
            'Burj Khalifa observation deck',
            'Desert safari with BBQ dinner',
            'Dubai Mall shopping spree',
            'Luxury yacht cruise',
            'Gold Souk visit'
        ],
        inclusions=[
            'Business class flights',
            '4 nights luxury accommodation',
            'All meals included',
            'Private chauffeur',
            'VIP experiences',
            'Travel insurance'
        ],
        exclusions=[
            'Personal shopping',
            'Optional helicopter tour',
            'Spa treatments'
        ],
        is_active=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=45)
    )
    packages.append(pkg2)
    
    # Package 3 - Maldives Honeymoon
    pkg3 = Package(
        id=str(uuid.uuid4()),
        name='Maldives Honeymoon Special',
        slug='maldives-honeymoon-special',
        description='Romantic escape to paradise. Overwater villas, pristine beaches, and unforgettable sunsets.',
        destination_city='Maldives',
        destination_country='Maldives',
        duration_days=6,
        duration_nights=5,
        starting_price=2499.00,
        price_per_person=2499.00,
        hotel_name='Conrad Maldives Rangali Island',
        hotel_rating=5,
        room_type='Overwater Villa',
        featured_image='https://images.unsplash.com/photo-1514282401047-d79a71a590e8',
        gallery_images=[
            'https://images.unsplash.com/photo-1514282401047-d79a71a590e8',
            'https://images.unsplash.com/photo-1573843981267-be1999ff37cd',
            'https://images.unsplash.com/photo-1589197331516-e4d5e5c1c9b0'
        ],
        highlights=[
            'Private overwater villa',
            'Couples spa treatment',
            'Sunset dolphin cruise',
            'Underwater restaurant dining',
            'Snorkeling with manta rays'
        ],
        inclusions=[
            'Seaplane transfers',
            '5 nights overwater villa',
            'All-inclusive meals',
            'Water sports',
            'Honeymoon amenities',
            'Travel insurance'
        ],
        is_active=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=30)
    )
    packages.append(pkg3)
    
    db.session.add_all(packages)
    db.session.commit()
    
    print(f"   ✅ Created {len(packages)} packages")
    return packages


def create_sample_bookings(users, packages):
    """Create sample bookings for users"""
    print("   Creating bookings...")
    
    bookings = []
    
    # Booking 1 - Confirmed flight for user 1
    booking1 = Booking(
        id=str(uuid.uuid4()),
        user_id=users[0].id,
        booking_reference=f'TGT-{random.randint(100000, 999999)}',
        booking_type='flight',
        status=BookingStatus.CONFIRMED,
        trip_type=TripType.ROUND_TRIP,
        origin='New York (JFK)',
        destination='London (LHR)',
        departure_date=(datetime.now() + timedelta(days=30)).date(),
        return_date=(datetime.now() + timedelta(days=37)).date(),
        airline='British Airways',
        flight_number='BA178',
        travel_class=TravelClass.BUSINESS,
        num_adults=2,
        num_children=0,
        num_infants=0,
        base_price=1800.00,
        service_fee=150.00,
        taxes=250.00,
        discount=0.00,
        total_price=2200.00,
        created_at=datetime.now(timezone.utc) - timedelta(days=15)
    )
    bookings.append(booking1)
    
    # Add passengers for booking1
    passenger1_1 = Passenger(
        id=str(uuid.uuid4()),
        booking_id=booking1.id,
        first_name='John',
        last_name='Doe',
        date_of_birth=datetime(1990, 5, 15).date(),
        passport_number='P123456789',
        nationality='American',
        passenger_type='adult'
    )
    passenger1_2 = Passenger(
        id=str(uuid.uuid4()),
        booking_id=booking1.id,
        first_name='Emily',
        last_name='Doe',
        date_of_birth=datetime(1992, 8, 20).date(),
        passport_number='P987654321',
        nationality='American',
        passenger_type='adult'
    )
    db.session.add_all([passenger1_1, passenger1_2])
    
    # Booking 2 - Pending booking for user 1
    booking2 = Booking(
        id=str(uuid.uuid4()),
        user_id=users[0].id,
        booking_reference=f'TGT-{random.randint(100000, 999999)}',
        booking_type='flight',
        status=BookingStatus.PENDING,
        trip_type=TripType.ONE_WAY,
        origin='Los Angeles (LAX)',
        destination='Tokyo (NRT)',
        departure_date=(datetime.now() + timedelta(days=60)).date(),
        airline='Japan Airlines',
        flight_number='JL061',
        travel_class=TravelClass.ECONOMY,
        num_adults=1,
        num_children=0,
        num_infants=0,
        base_price=850.00,
        service_fee=75.00,
        taxes=125.00,
        discount=0.00,
        total_price=1050.00,
        created_at=datetime.now(timezone.utc) - timedelta(days=2)
    )
    bookings.append(booking2)
    
    # Booking 3 - Package booking for user 2 (Bali)
    booking3 = Booking(
        id=str(uuid.uuid4()),
        user_id=users[1].id,
        package_id=packages[0].id,
        booking_reference=f'TGT-{random.randint(100000, 999999)}',
        booking_type='package',
        status=BookingStatus.CONFIRMED,
        departure_date=(datetime.now() + timedelta(days=45)).date(),
        return_date=(datetime.now() + timedelta(days=52)).date(),
        num_adults=2,
        num_children=1,
        num_infants=0,
        base_price=3897.00,  # 1299 * 3 people
        service_fee=200.00,
        taxes=300.00,
        discount=100.00,
        total_price=4297.00,
        created_at=datetime.now(timezone.utc) - timedelta(days=20)
    )
    bookings.append(booking3)
    
    # Booking 4 - Completed booking for user 2
    booking4 = Booking(
        id=str(uuid.uuid4()),
        user_id=users[1].id,
        booking_reference=f'TGT-{random.randint(100000, 999999)}',
        booking_type='flight',
        status=BookingStatus.COMPLETED,
        trip_type=TripType.ROUND_TRIP,
        origin='London (LHR)',
        destination='Paris (CDG)',
        departure_date=(datetime.now() - timedelta(days=10)).date(),
        return_date=(datetime.now() - timedelta(days=7)).date(),
        airline='Air France',
        flight_number='AF1234',
        travel_class=TravelClass.ECONOMY,
        num_adults=1,
        num_children=0,
        num_infants=0,
        base_price=180.00,
        service_fee=25.00,
        taxes=35.00,
        discount=0.00,
        total_price=240.00,
        created_at=datetime.now(timezone.utc) - timedelta(days=25)
    )
    bookings.append(booking4)
    
    # Booking 5 - Cancelled booking for user 3
    booking5 = Booking(
        id=str(uuid.uuid4()),
        user_id=users[2].id,
        booking_reference=f'TGT-{random.randint(100000, 999999)}',
        booking_type='flight',
        status=BookingStatus.CANCELLED,
        trip_type=TripType.ROUND_TRIP,
        origin='Toronto (YYZ)',
        destination='Vancouver (YVR)',
        departure_date=(datetime.now() + timedelta(days=20)).date(),
        return_date=(datetime.now() + timedelta(days=25)).date(),
        airline='Air Canada',
        flight_number='AC101',
        travel_class=TravelClass.BUSINESS,
        num_adults=1,
        num_children=0,
        num_infants=0,
        base_price=650.00,
        service_fee=50.00,
        taxes=80.00,
        discount=0.00,
        total_price=780.00,
        created_at=datetime.now(timezone.utc) - timedelta(days=30)
    )
    bookings.append(booking5)
    
    # Booking 6 - Package booking for user 3 (Dubai)
    booking6 = Booking(
        id=str(uuid.uuid4()),
        user_id=users[2].id,
        package_id=packages[1].id,
        booking_reference=f'TGT-{random.randint(100000, 999999)}',
        booking_type='package',
        status=BookingStatus.CONFIRMED,
        departure_date=(datetime.now() + timedelta(days=90)).date(),
        return_date=(datetime.now() + timedelta(days=95)).date(),
        num_adults=2,
        num_children=0,
        num_infants=0,
        base_price=3798.00,  # 1899 * 2
        service_fee=250.00,
        taxes=350.00,
        discount=150.00,
        total_price=4248.00,
        created_at=datetime.now(timezone.utc) - timedelta(days=5)
    )
    bookings.append(booking6)
    
    db.session.add_all(bookings)
    db.session.commit()
    
    print(f"   ✅ Created {len(bookings)} bookings")
    return bookings


def create_sample_payments(users, bookings):
    """Create sample payment records"""
    print("   Creating payments...")
    
    payments = []
    
    # Payment for booking 1
    payment1 = Payment(
        id=str(uuid.uuid4()),
        payment_reference=f'PAY-{random.randint(100000, 999999)}',
        user_id=users[0].id,
        booking_id=bookings[0].id,
        amount=2200.00,
        currency='USD',
        payment_method='credit_card',
        status=PaymentStatus.PAID,
        stripe_payment_intent_id=f'pi_{random.randint(100000000000, 999999999999)}',
        paid_at=datetime.now(timezone.utc) - timedelta(days=15),
        created_at=datetime.now(timezone.utc) - timedelta(days=15)
    )
    payments.append(payment1)
    
    # Payment for booking 3
    payment3 = Payment(
        id=str(uuid.uuid4()),
        payment_reference=f'PAY-{random.randint(100000, 999999)}',
        user_id=users[1].id,
        booking_id=bookings[2].id,
        amount=4297.00,
        currency='USD',
        payment_method='credit_card',
        status=PaymentStatus.PAID,
        stripe_payment_intent_id=f'pi_{random.randint(100000000000, 999999999999)}',
        paid_at=datetime.now(timezone.utc) - timedelta(days=20),
        created_at=datetime.now(timezone.utc) - timedelta(days=20)
    )
    payments.append(payment3)
    
    # Payment for booking 4
    payment4 = Payment(
        id=str(uuid.uuid4()),
        payment_reference=f'PAY-{random.randint(100000, 999999)}',
        user_id=users[1].id,
        booking_id=bookings[3].id,
        amount=240.00,
        currency='USD',
        payment_method='paypal',
        status=PaymentStatus.PAID,
        paid_at=datetime.now(timezone.utc) - timedelta(days=25),
        created_at=datetime.now(timezone.utc) - timedelta(days=25)
    )
    payments.append(payment4)
    
    # Payment for booking 6
    payment6 = Payment(
        id=str(uuid.uuid4()),
        payment_reference=f'PAY-{random.randint(100000, 999999)}',
        user_id=users[2].id,
        booking_id=bookings[5].id,
        amount=4248.00,
        currency='USD',
        payment_method='credit_card',
        status=PaymentStatus.PAID,
        stripe_payment_intent_id=f'pi_{random.randint(100000000000, 999999999999)}',
        paid_at=datetime.now(timezone.utc) - timedelta(days=5),
        created_at=datetime.now(timezone.utc) - timedelta(days=5)
    )
    payments.append(payment6)
    
    db.session.add_all(payments)
    db.session.commit()
    
    print(f"   ✅ Created {len(payments)} payments")
    return payments


def create_sample_notifications(users, bookings):
    """Create sample notifications"""
    print("   Creating notifications...")
    
    notifications = []
    
    # Notification 1 - Booking confirmation
    notif1 = Notification(
        id=str(uuid.uuid4()),
        user_id=users[0].id,
        type='booking_confirmed',
        title='Booking Confirmed',
        message=f'Your booking {bookings[0].booking_reference} has been confirmed!',
        is_read=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=15)
    )
    notifications.append(notif1)
    
    # Notification 2 - Unread notification
    notif2 = Notification(
        id=str(uuid.uuid4()),
        user_id=users[0].id,
        type='payment_received',
        title='Payment Received',
        message='Your payment of $2,200.00 has been processed successfully.',
        is_read=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    notifications.append(notif2)
    
    # Notification 3 - Upcoming trip
    notif3 = Notification(
        id=str(uuid.uuid4()),
        user_id=users[1].id,
        type='booking_reminder',
        title='Upcoming Trip Reminder',
        message='Your trip to Bali is coming up in 45 days. Don\'t forget to check your travel documents!',
        is_read=False,
        created_at=datetime.now(timezone.utc) - timedelta(hours=12)
    )
    notifications.append(notif3)
    
    # Notification 4 - Subscription renewal
    notif4 = Notification(
        id=str(uuid.uuid4()),
        user_id=users[2].id,
        type='subscription_renewed',
        title='Subscription Renewed',
        message='Your Gold subscription has been renewed successfully.',
        is_read=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=15)
    )
    notifications.append(notif4)
    
    db.session.add_all(notifications)
    db.session.commit()
    
    print(f"   ✅ Created {len(notifications)} notifications")
    return notifications


def create_sample_settings():
    """Create sample system settings"""
    print("   Creating settings...")
    
    settings = []
    
    # General settings
    setting1 = Settings(
        key='site_name',
        value='Thrive Travel',
        description='Website name'
    )
    settings.append(setting1)
    
    setting2 = Settings(
        key='support_email',
        value='support@thrivetravel.com',
        description='Support email address'
    )
    settings.append(setting2)
    
    db.session.add_all(settings)
    db.session.commit()
    
    print(f"   ✅ Created {len(settings)} settings")
    return settings
