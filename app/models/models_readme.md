# Thrive Global Travel & Tours - Database Models Documentation

## Table of Contents
1. [Overview](#overview)
2. [User Model](#user-model)
3. [Booking Model](#booking-model)
4. [Passenger Model](#passenger-model)
5. [Package Model](#package-model)
6. [Payment Model](#payment-model)
7. [Quote Model](#quote-model)
8. [Notification Model](#notification-model)
9. [AuditLog Model](#auditlog-model)
10. [Settings Model](#settings-model)
11. [Common Customizations](#common-customizations)
12. [Usage Flow Examples](#usage-flow-examples)

---

## Overview

The Thrive Global Travel database schema consists of 9 core models designed to handle all aspects of travel booking, from user management to payment processing. All models use UUID primary keys for security and scalability, include timestamps for auditing, and follow RESTful best practices.

### Design Principles
- **Security First**: Sensitive data encrypted, audit trails for all critical actions
- **Scalability**: UUID keys, indexed fields, optimized relationships
- **Flexibility**: JSON fields for extensible data, enum types for consistency
- **Business Logic**: Built-in validation, automatic calculations, status workflows

---

## User Model

### Purpose
Manages all system users including customers, corporate clients, travel agents, and administrators. Handles authentication, profile management, subscriptions, and referral system.

### Key Fields

#### Authentication & Identity
```python
id: UUID (Primary Key)
email: String(120) - Unique, indexed
password_hash: String(255) - Never store plain passwords
first_name: String(50)
last_name: String(50)
phone: String(20)
role: Enum(UserRole) - customer, corporate, admin, agent
```

#### Profile & Travel Information
```python
date_of_birth: Date
passport_number: String(50)
passport_expiry: Date
nationality: String(50)
preferred_airline: String(100)
frequent_flyer_numbers: JSON - {"AA": "12345", "DL": "67890"}
dietary_preferences: String(200)
special_assistance: Text
```

#### Subscription Management
```python
subscription_tier: Enum(SubscriptionTier) - none, bronze, silver, gold
subscription_start: DateTime
subscription_end: DateTime
monthly_bookings_used: Integer - Resets monthly
```

#### Corporate Features
```python
company_name: String(200)
company_tax_id: String(50)
billing_address: Text
```

#### Referral System
```python
referral_code: String(20) - Unique code for sharing
referred_by: ForeignKey(User) - Who referred this user
referral_credits: Numeric(10,2) - Earned credit balance
```

### Important Methods

#### `set_password(password)`
Hashes and stores password securely using Werkzeug.

#### `check_password(password)`
Validates login credentials.

#### `has_active_subscription()`
Returns boolean indicating if subscription is current.

#### `can_book()`
Checks if user has remaining bookings in their subscription tier.

#### `to_dict()`
Returns JSON-serializable user data (excludes sensitive info).

### Relationships
```python
bookings → Booking (one-to-many)
payments → Payment (one-to-many)
notifications → Notification (one-to-many)
referrals → User (self-referencing)
handled_bookings → Booking (as agent)
```

### Customizations

#### Add Social Login
```python
google_id = db.Column(db.String(100), unique=True)
facebook_id = db.Column(db.String(100), unique=True)
apple_id = db.Column(db.String(100), unique=True)
```

#### Add User Preferences
```python
preferred_currency = db.Column(db.String(3), default='USD')
preferred_language = db.Column(db.String(5), default='en')
notification_preferences = db.Column(db.JSON)
```

#### Add Loyalty Program
```python
loyalty_points = db.Column(db.Integer, default=0)
loyalty_tier = db.Column(db.String(20))  # bronze, silver, gold, platinum
lifetime_bookings = db.Column(db.Integer, default=0)
lifetime_spend = db.Column(db.Numeric(12, 2), default=0.00)
```

### Usage Example
```python
# Create new customer
user = User(
    email='john@example.com',
    first_name='John',
    last_name='Doe',
    phone='+1234567890',
    role=UserRole.CUSTOMER
)
user.set_password('secure_password_123')
user.referral_code = ReferralManager.generate_referral_code(user.id)

db.session.add(user)
db.session.commit()

# Activate subscription
SubscriptionManager.activate_subscription(user, 'silver', duration_months=1)

# Check booking eligibility
can_book, message = user.can_book()
if can_book:
    user.monthly_bookings_used += 1
    db.session.commit()
```

---

## Booking Model

### Purpose
Core business entity representing flight bookings, package tours, hotel reservations, and custom travel arrangements. Tracks complete trip lifecycle from quote to completion.

### Key Fields

#### Identification
```python
id: UUID (Primary Key)
booking_reference: String(20) - Unique code like "TGT-ABC123"
user_id: ForeignKey(User)
booking_type: String(20) - flight, package, hotel, custom
status: Enum(BookingStatus) - pending, confirmed, cancelled, completed, refunded
```

#### Trip Details
```python
trip_type: Enum(TripType) - one_way, round_trip, multi_city
origin: String(100) - Airport code or city
destination: String(100)
departure_date: DateTime
return_date: DateTime (nullable)
```

#### Flight Information
```python
airline: String(100)
flight_number: String(20)
travel_class: Enum(TravelClass) - economy, premium_economy, business, first_class
num_adults: Integer
num_children: Integer
num_infants: Integer
```

#### Pricing
```python
base_price: Numeric(10,2) - Ticket/package cost
service_fee: Numeric(10,2) - Your booking fee
taxes: Numeric(10,2)
discount: Numeric(10,2)
total_price: Numeric(10,2) - Calculated total
```

#### Operational
```python
is_urgent: Boolean - Within 7 days
special_requests: Text
assigned_agent_id: ForeignKey(User)
airline_confirmation: String(50)
ticket_numbers: JSON - ["1234567890123", "9876543210987"]
```

### Important Methods

#### `generate_booking_reference()`
Static method that creates unique references like "TGT-ABC123".

#### `calculate_total()`
Computes total_price from base + fees + taxes - discounts.

#### `get_total_passengers()`
Returns sum of adults, children, and infants.

#### `to_dict()`
Returns JSON-serializable booking data for API responses.

### Relationships
```python
customer → User (many-to-one)
passengers → Passenger (one-to-many)
payments → Payment (one-to-many)
package → Package (many-to-one, optional)
agent → User (many-to-one, optional)
```

### Customizations

#### Add Multi-City Support
```python
segments = db.Column(db.JSON)
# [
#   {"origin": "JFK", "destination": "LHR", "date": "2025-06-01"},
#   {"origin": "LHR", "destination": "PAR", "date": "2025-06-05"}
# ]
```

#### Add Seat Selection
```python
seat_preferences = db.Column(db.JSON)
# {"passenger_id": "seat_number", "abc-123": "12A"}
```

#### Add Baggage Tracking
```python
baggage_allowance = db.Column(db.JSON)
# {"checked": 2, "carry_on": 1, "weight_kg": 23}
extra_baggage_fee = db.Column(db.Numeric(10, 2))
```

#### Add Insurance
```python
has_insurance = db.Column(db.Boolean, default=False)
insurance_provider = db.Column(db.String(100))
insurance_policy_number = db.Column(db.String(50))
insurance_cost = db.Column(db.Numeric(10, 2))
```

### Usage Example
```python
# Create flight booking
booking = Booking(
    user_id=user.id,
    booking_type='flight',
    trip_type=TripType.ROUND_TRIP,
    origin='JFK',
    destination='LHR',
    departure_date=datetime(2025, 7, 15),
    return_date=datetime(2025, 7, 22),
    travel_class=TravelClass.ECONOMY,
    num_adults=2,
    num_children=1,
    base_price=Decimal('1500.00')
)

# Calculate service fee
is_domestic = BookingManager.is_domestic_flight('JFK', 'LHR')
booking.service_fee = PricingCalculator.calculate_flight_service_fee(
    is_domestic=is_domestic,
    num_passengers=booking.get_total_passengers(),
    is_urgent=False
)

# Calculate total
booking.calculate_total()

db.session.add(booking)
db.session.commit()

# Update status to confirmed
booking.status = BookingStatus.CONFIRMED
booking.confirmed_at = datetime.utcnow()
booking.airline_confirmation = 'ABC123XYZ'
db.session.commit()

# Send notification
NotificationService.send_booking_confirmation(booking)
```

---

## Passenger Model

### Purpose
Stores individual passenger information for each booking. Required for ticket issuance and TSA/immigration compliance.

### Key Fields

#### Personal Information
```python
id: UUID (Primary Key)
booking_id: ForeignKey(Booking)
title: String(10) - Mr, Mrs, Ms, Dr, Prof
first_name: String(100)
middle_name: String(100)
last_name: String(100)
date_of_birth: Date
gender: String(10)
nationality: String(50)
```

#### Travel Documents
```python
passport_number: String(50)
passport_expiry: Date
passport_country: String(50)
```

#### Ticketing
```python
passenger_type: String(20) - adult, child, infant
ticket_number: String(50) - Airline ticket number
seat_number: String(10) - Assigned seat
frequent_flyer_number: String(50)
```

#### Special Requirements
```python
meal_preference: String(50) - vegetarian, halal, kosher, etc.
special_assistance: String(200) - wheelchair, visual impairment, etc.
```

### Important Methods

#### `get_full_name()`
Returns formatted full name (title + first + middle + last).

#### `to_dict()`
Returns JSON-serializable passenger data.

### Customizations

#### Add Known Traveler Numbers
```python
tsa_precheck_number = db.Column(db.String(20))
global_entry_number = db.Column(db.String(20))
nexus_number = db.Column(db.String(20))
```

#### Add Emergency Contact
```python
emergency_contact_name = db.Column(db.String(100))
emergency_contact_phone = db.Column(db.String(20))
emergency_contact_relation = db.Column(db.String(50))
```

#### Add Health Information
```python
medical_conditions = db.Column(db.Text)
medications = db.Column(db.Text)
allergies = db.Column(db.Text)
```

### Usage Example
```python
# Add passengers to booking
passengers_data = [
    {
        'title': 'Mr',
        'first_name': 'John',
        'last_name': 'Doe',
        'date_of_birth': datetime(1985, 5, 15).date(),
        'gender': 'Male',
        'nationality': 'USA',
        'passport_number': 'N12345678',
        'passport_expiry': datetime(2030, 5, 15).date(),
        'passenger_type': 'adult'
    },
    {
        'title': 'Mrs',
        'first_name': 'Jane',
        'last_name': 'Doe',
        'date_of_birth': datetime(1987, 8, 20).date(),
        'gender': 'Female',
        'nationality': 'USA',
        'passport_number': 'N98765432',
        'passport_expiry': datetime(2029, 8, 20).date(),
        'passenger_type': 'adult',
        'meal_preference': 'vegetarian'
    }
]

for data in passengers_data:
    passenger = Passenger(booking_id=booking.id, **data)
    db.session.add(passenger)

db.session.commit()
```

---

## Package Model

### Purpose
Represents curated tour packages like the "Dubai Luxury Escape". Includes itinerary, pricing, availability, and marketing content.

### Key Fields

#### Basic Information
```python
id: UUID (Primary Key)
name: String(200) - "Dubai Luxury Escape"
slug: String(200) - URL-friendly "dubai-luxury-escape"
description: Text - Full package description
```

#### Destination
```python
destination_city: String(100) - "Dubai"
destination_country: String(100) - "United Arab Emirates"
```

#### Duration & Pricing
```python
duration_days: Integer - 5
duration_nights: Integer - 4
starting_price: Numeric(10,2) - $1,899
price_per_person: Numeric(10,2)
```

#### Package Content
```python
highlights: JSON - ["Desert Safari", "Burj Khalifa", "Yacht Cruise"]
inclusions: JSON - ["Hotel", "Breakfast", "Tours", "Transfers"]
exclusions: JSON - ["Flights", "Travel Insurance", "Lunch/Dinner"]
itinerary: JSON - Day-by-day breakdown
```

#### Accommodation
```python
hotel_name: String(200)
hotel_rating: Integer - Star rating 1-5
room_type: String(100) - "Deluxe Double"
```

#### Availability
```python
is_active: Boolean
available_from: Date
available_until: Date
max_capacity: Integer - Per departure
min_booking: Integer - Minimum group size
```

#### Marketing
```python
featured_image: String(500) - URL to main image
gallery_images: JSON - Array of image URLs
meta_title: String(200) - SEO title
meta_description: Text - SEO description
view_count: Integer
booking_count: Integer
```

### Important Methods

#### `to_dict()`
Returns comprehensive package data for API responses.

### Customizations

#### Add Seasonal Pricing
```python
pricing_calendar = db.Column(db.JSON)
# {
#   "2025-06": {"price": 1899, "availability": 20},
#   "2025-07": {"price": 2199, "availability": 15},
#   "2025-12": {"price": 2499, "availability": 30}
# }
```

#### Add Departure Dates
```python
departure_dates = db.Column(db.JSON)
# ["2025-06-15", "2025-06-22", "2025-07-01"]
guaranteed_departures = db.Column(db.JSON)
```

#### Add Reviews & Ratings
```python
average_rating = db.Column(db.Numeric(3, 2))
total_reviews = db.Column(db.Integer, default=0)
reviews = relationship('PackageReview', backref='package')
```

#### Add Addons
```python
available_addons = db.Column(db.JSON)
# [
#   {"name": "Hot Air Balloon", "price": 250, "description": "..."},
#   {"name": "Private Guide", "price": 150, "description": "..."}
# ]
```

### Usage Example
```python
# Create Dubai package
dubai_package = Package(
    name="Dubai Luxury Escape",
    slug="dubai-luxury-escape",
    description="Experience the best of Dubai...",
    destination_city="Dubai",
    destination_country="United Arab Emirates",
    duration_days=5,
    duration_nights=4,
    starting_price=Decimal('1899.00'),
    price_per_person=Decimal('1899.00'),
    highlights=[
        "4-star hotel in Downtown Dubai",
        "Desert Safari with BBQ dinner",
        "Dubai Marina Yacht Cruise",
        "Burj Khalifa At-The-Top experience",
        "Dubai Mall & Fountain show",
        "Abu Dhabi Grand Mosque tour"
    ],
    inclusions=[
        "4-star hotel accommodation",
        "Daily breakfast",
        "Airport transfers",
        "All tours and activities listed",
        "Professional English-speaking guide"
    ],
    exclusions=[
        "International flights",
        "Travel insurance",
        "Lunch and dinner (except Desert Safari BBQ)",
        "Personal expenses",
        "Optional activities"
    ],
    itinerary={
        "day_1": {
            "title": "Arrival & Check-in",
            "activities": ["Airport pickup", "Hotel check-in", "Leisure time"]
        },
        "day_2": {
            "title": "Modern Dubai Tour",
            "activities": ["Burj Khalifa", "Dubai Mall", "Fountain show"]
        }
        # ... more days
    },
    hotel_name="Downtown Dubai Hotel",
    hotel_rating=4,
    room_type="Deluxe Double Room",
    is_active=True,
    featured_image="https://example.com/dubai-main.jpg",
    gallery_images=[
        "https://example.com/dubai-1.jpg",
        "https://example.com/dubai-2.jpg"
    ]
)

db.session.add(dubai_package)
db.session.commit()

# Book package for 2 people
package_booking = Booking(
    user_id=user.id,
    booking_type='package',
    package_id=dubai_package.id,
    departure_date=datetime(2025, 8, 15),
    num_adults=2,
    base_price=dubai_package.price_per_person * 2,
    service_fee=Decimal('100.00')
)
package_booking.calculate_total()
db.session.add(package_booking)
db.session.commit()
```

---

## Payment Model

### Purpose
Tracks all financial transactions including payments, refunds, and payment processing details. Integrates with Stripe and other payment gateways.

### Key Fields

#### Identification
```python
id: UUID (Primary Key)
payment_reference: String(50) - Unique payment ID
booking_id: ForeignKey(Booking)
user_id: ForeignKey(User)
```

#### Payment Details
```python
amount: Numeric(10,2)
currency: String(3) - USD, EUR, GBP, etc.
payment_method: String(50) - card, stripe, paypal, bank_transfer
status: Enum(PaymentStatus) - pending, paid, failed, refunded, partial
```

#### Gateway Integration
```python
stripe_payment_intent_id: String(100)
stripe_charge_id: String(100)
transaction_id: String(100) - External reference
```

#### Card Information (Secure)
```python
card_last4: String(4) - Only last 4 digits
card_brand: String(20) - visa, mastercard, amex
```

#### Metadata & Refunds
```python
payment_metadata: JSON - Additional gateway data
failure_reason: Text
refund_amount: Numeric(10,2)
refund_reason: Text
refunded_at: DateTime
```

### Important Methods

#### `to_dict()`
Returns safe payment data (no sensitive info).

### Customizations

#### Add Payment Plans
```python
is_installment = db.Column(db.Boolean, default=False)
installment_plan = db.Column(db.JSON)
# {
#   "total_installments": 3,
#   "current_installment": 1,
#   "installment_amount": 633.00,
#   "next_due_date": "2025-08-01"
# }
```

#### Add Multiple Payment Methods
```python
split_payments = db.Column(db.JSON)
# [
#   {"method": "card", "amount": 1000},
#   {"method": "credit", "amount": 500}
# ]
```

#### Add Fraud Detection
```python
fraud_score = db.Column(db.Integer)
fraud_checks = db.Column(db.JSON)
is_flagged = db.Column(db.Boolean, default=False)
```

### Usage Example
```python
# Create payment for booking
payment = Payment(
    booking_id=booking.id,
    user_id=user.id,
    amount=booking.total_price,
    currency='USD',
    payment_method='stripe',
    status=PaymentStatus.PENDING
)
payment.payment_reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"

db.session.add(payment)
db.session.commit()

# Process with Stripe
intent = PaymentProcessor.create_payment_intent(
    amount=payment.amount,
    currency=payment.currency,
    metadata={'payment_id': payment.id, 'booking_id': booking.id}
)

if intent:
    payment.stripe_payment_intent_id = intent.id
    db.session.commit()

# After successful payment
payment.status = PaymentStatus.PAID
payment.paid_at = datetime.utcnow()
payment.card_last4 = '4242'
payment.card_brand = 'visa'
db.session.commit()

# Send confirmation
NotificationService.send_payment_received(payment)

# Process refund if needed
PaymentProcessor.process_refund(
    payment_id=payment.id,
    amount=Decimal('500.00'),
    reason='Partial cancellation'
)
```

---

## Quote Model

### Purpose
Manages quote requests from potential customers. Allows users to request pricing before committing to a booking.

### Key Fields

#### Contact Information
```python
id: UUID (Primary Key)
quote_reference: String(20) - "QTE-ABC123"
email: String(120)
phone: String(20)
name: String(100)
```

#### Trip Requirements
```python
origin: String(100)
destination: String(100)
departure_date: Date
return_date: Date (nullable)
trip_type: Enum(TripType)
num_adults: Integer
num_children: Integer
num_infants: Integer
```

#### Preferences
```python
preferred_class: Enum(TravelClass)
preferred_airline: String(100)
is_flexible: Boolean - Flexible with dates
special_requests: Text
```

#### Quote Response
```python
status: String(20) - pending, sent, accepted, expired
quoted_price: Numeric(10,2)
service_fee: Numeric(10,2)
total_price: Numeric(10,2)
agent_notes: Text
quote_details: JSON - Flight options, alternatives
```

#### Conversion Tracking
```python
converted_to_booking_id: ForeignKey(Booking)
expires_at: DateTime
quoted_at: DateTime
```

### Important Methods

#### `is_expired()`
Checks if quote has passed expiration date.

#### `to_dict()`
Returns JSON-serializable quote data.

### Customizations

#### Add Follow-up System
```python
follow_up_count = db.Column(db.Integer, default=0)
last_follow_up = db.Column(db.DateTime)
next_follow_up = db.Column(db.DateTime)
```

#### Add Alternative Options
```python
alternatives = db.Column(db.JSON)
# [
#   {"airline": "AA", "price": 850, "stops": 1},
#   {"airline": "DL", "price": 920, "stops": 0}
# ]
```

### Usage Example
```python
# Customer submits quote request
quote = Quote(
    email='customer@example.com',
    phone='+1234567890',
    name='Sarah Johnson',
    origin='LAX',
    destination='NRT',
    departure_date=datetime(2025, 9, 15).date(),
    return_date=datetime(2025, 9, 25).date(),
    trip_type=TripType.ROUND_TRIP,
    num_adults=2,
    preferred_class=TravelClass.BUSINESS,
    special_requests='Window seats preferred'
)
quote.quote_reference = BookingManager.generate_reference_code('QTE')
quote.expires_at = datetime.utcnow() + timedelta(days=7)

db.session.add(quote)
db.session.commit()

# Agent provides quote
quote.status = 'sent'
quote.quoted_price = Decimal('3200.00')
quote.service_fee = Decimal('100.00')
quote.total_price = Decimal('3300.00')
quote.quoted_at = datetime.utcnow()
quote.agent_notes = 'Best option: United direct flight'
quote.quote_details = {
    'flight_options': [
        {
            'airline': 'United',
            'flight_number': 'UA79',
            'departure': '2025-09-15 11:00',
            'arrival': '2025-09-16 15:30',
            'price': 1600
        }
    ]
}
db.session.commit()

# Send quote email
EmailService.send_email(
    to=quote.email,
    subject=f'Your Travel Quote - {quote.quote_reference}',
    body=f'Total price: ${quote.total_price}'
)
```

---

## Notification Model

### Purpose
Manages in-app notifications, email alerts, and SMS messages to keep users informed about bookings, payments, and updates.

### Key Fields

```python
id: UUID (Primary Key)
user_id: ForeignKey(User)
type: String(50) - booking_confirmed, payment_received, etc.
title: String(200)
message: Text
link_url: String(500) - Deep link to related resource
booking_id: ForeignKey(Booking) (optional)
is_read: Boolean
read_at: DateTime
sent_via_email: Boolean
sent_via_sms: Boolean
```

### Important Methods

#### `to_dict()`
Returns notification data for API responses.

### Customizations

#### Add Notification Channels
```python
sent_via_push = db.Column(db.Boolean, default=False)
sent_via_whatsapp = db.Column(db.Boolean, default=False)
delivery_status = db.Column(db.String(20))
```

#### Add Actionable Notifications
```python
action_required = db.Column(db.Boolean, default=False)
action_type = db.Column(db.String(50))  # confirm, pay, review
action_url = db.Column(db.String(500))
action_expires_at = db.Column(db.DateTime)
```

### Usage Example
```python
# System sends notification
notification = NotificationService.create_notification(
    user_id=user.id,
    notification_type='booking_reminder',
    title='Upcoming Trip Reminder',
    message='Your trip to Dubai departs in 7 days. Check-in opens in 24 hours!',
    booking_id=booking.id,
    link_url=f'/bookings/{booking.id}'
)

# Mark as read
notification.is_read = True
notification.read_at = datetime.utcnow()
db.session.commit()

# Get unread count
unread_count = Notification.query.filter_by(
    user_id=user.id,
    is_read=False
).count()
```

---

## AuditLog Model

### Purpose
Security and compliance audit trail tracking all critical system actions for accountability and debugging.

### Key Fields

```python
id: UUID (Primary Key)
user_id: ForeignKey(User)
action: String(100) - 'user_login', 'booking_created', etc.
entity_type: String(50) - booking, payment, user
entity_id: String(36)
description: Text
changes: JSON - Before/after values
ip_address: String(45)
user_agent: String(500)
created_at: DateTime
```

### Customizations

#### Add Request Details
```python
request_method = db.Column(db.String(10))  # GET, POST, PUT, DELETE
request_path = db.Column(db.String(500))
response_status = db.Column(db.Integer)
```

### Usage Example
```python
# Log important action
AuditLogger.log_action(
    user_id=current_user.id,
    action='booking_created',
    entity_type='booking',
    entity_id=booking.id,
    description=f'Created booking {booking.booking_reference}',
    changes={
        'before': None,
        'after': booking.to_dict()
    },
    ip_address=request.remote_addr,
    user_agent=request.user_agent.string
)
```

---

## Settings Model

### Purpose
Stores application configuration with type-safe value handling.

### Key Fields

```python
id: Integer (Primary Key)
key: String(100) - Unique setting identifier
value: Text - Stored as string
data_type: String(20) - string, int, float, bool, json
description: String(500)
```

### Important Methods

#### `get_value(key, default=None)`
Retrieves and type-converts setting value.

#### `set_value(key, value, data_type, description)`
Stores setting with automatic type conversion.

### Usage Example
```python
# Set configurations
Settings.set_value('urgent_booking_days', 7, 'int', 'Days to consider booking urgent')
Settings.set_value('max_passengers', 9, 'int', 'Maximum passengers per booking')
Settings.set_value('enable_sms', True, 'bool', 'Enable SMS notifications')
Settings.set_value('supported_currencies', ['USD', 'EUR', 'GBP'], 'json')

# Retrieve values
urgent_days = Settings.get_value('urgent_booking_days', default=7)
sms_enabled = Settings.get_value('enable_sms', default=False)
currencies = Settings.get_value('supported_currencies', default=['USD'])
```

---

## Common Customizations

### Multi-Currency Support
Add currency fields to User, Booking, Payment models:
```python
preferred_currency = db.Column(db.String(3), default='USD')
exchange_rate = db.Column(db.Numeric(10, 6))
original_currency = db.Column(db.String(3))
```

### Multi-Language Support
Add translation fields:
```python
translations = db.Column(db.JSON)
# {"en": {...}, "es": {...}, "fr": {...}}
```

### API Rate Limiting
Track API usage:
```python
class APIUsage(db.Model):
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    endpoint = db.Column(db.String(200))
    request_count = db.Column(db.Integer)
    last_reset = db.Column(db.DateTime)
```

---

## Usage Flow Examples

### Complete Booking Flow

```python
# 1. User Registration
user = User(email='jane@example.com', first_name='Jane', last_name='Smith')
user.set_password('secure123')
user.referral_code = ReferralManager.generate_referral_code(user.id)
db.session.add(user)
db.session.commit()

# 2. Quote Request
quote = Quote(
    email=user.email,
    name=user.get_full_name(),
    origin='JFK',
    destination='