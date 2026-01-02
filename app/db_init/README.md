# Database Initialization Guide

## Overview

This directory contains scripts for initializing the Thrive Travel database with tables and sample data for testing and development.

## Files

- `__init__.py` - Package initialization
- `init_db.py` - Main initialization logic
- `sample_data.py` - Sample data generation functions
- `cli.py` - Flask CLI commands

## Quick Start

### 1. Initialize Database with Sample Data

```bash
cd backend
source venv/bin/activate
flask db-manage init
```

This will:
- Create all database tables
- Populate with sample users, bookings, packages, payments, and notifications

### 2. Reset Database (Drop & Recreate)

```bash
flask db-manage reset
```

⚠️ **Warning**: This will delete ALL existing data!

### 3. Clear Database (Drop Tables Only)

```bash
flask db-manage clear
```

### 4. Initialize Without Sample Data

```bash
flask db-manage init --no-sample-data
```

## Sample Data Created

### Users (5 total)

| Email | Password | Role | Subscription | Bookings |
|-------|----------|------|--------------|----------|
| john.doe@example.com | password123 | Customer | Bronze | 2 |
| jane.smith@example.com | password123 | Customer | Silver | 2 |
| mike.johnson@example.com | password123 | Customer | Gold | 2 |
| sarah.williams@example.com | password123 | Customer | None | 0 |
| admin@thrivetravel.com | admin123 | Admin | Gold | 0 |

### Packages (3 total)

1. **Bali Paradise Getaway** - $1,299/person
   - 7 Days, 6 Nights
   - Grand Hyatt Bali
   - Includes temples, beaches, rice terraces

2. **Dubai Luxury Experience** - $1,899/person
   - 5 Days, 4 Nights
   - Burj Al Arab
   - Desert safari, Burj Khalifa, luxury shopping

3. **Maldives Honeymoon Special** - $2,499/person
   - 6 Days, 5 Nights
   - Conrad Maldives
   - Overwater villas, couples spa, underwater dining

### Bookings (6 total)

- **Confirmed**: 3 bookings (flights + packages)
- **Pending**: 1 booking
- **Completed**: 1 booking
- **Cancelled**: 1 booking

### Payments (4 total)

- All confirmed bookings have associated payments
- Mix of credit card and PayPal payments
- Stripe payment intent IDs included

### Notifications (4 total)

- Booking confirmations
- Payment receipts
- Trip reminders
- Subscription renewals

## Testing the Dashboard

After initialization, you can test the dashboard with:

1. **Login** as any test user (see table above)
2. **Navigate** to `/dashboard`
3. **View**:
   - Dashboard stats (bookings, spending, etc.)
   - My Bookings (with filters)
   - My Trips & Tours
   - Profile information
   - Notifications

## Data Characteristics

### Realistic Data
- Proper date ranges (past, present, future)
- Realistic prices and fees
- Valid booking references
- Complete passenger information
- Proper foreign key relationships

### Subscription Tiers
- **Bronze**: 6 bookings/month, 5% discount
- **Silver**: 15 bookings/month, 10% discount, priority support
- **Gold**: Unlimited bookings, 15% discount, 24/7 support

### Booking Statuses
- **Pending**: Awaiting payment
- **Confirmed**: Paid and confirmed
- **Completed**: Trip finished
- **Cancelled**: Cancelled with refund

## Programmatic Usage

You can also use these functions in your code:

```python
from app.db_init import init_database, clear_database
from app.db_init.sample_data import create_sample_users

# Initialize with sample data
init_database(with_sample_data=True)

# Initialize without sample data
init_database(with_sample_data=False)

# Clear database
clear_database()

# Create only users
users = create_sample_users()
```

## Troubleshooting

### Error: "No module named 'app.db_init'"

Make sure you're in the backend directory and the virtual environment is activated:

```bash
cd backend
source venv/bin/activate
```

### Error: "Table already exists"

If tables already exist, use reset instead of init:

```bash
flask db-manage reset
```

### Error: "Foreign key constraint fails"

This usually means data is being created in the wrong order. The sample data functions handle this automatically, but if you're creating custom data, ensure:

1. Users are created first
2. Packages are created before bookings
3. Bookings are created before payments/passengers

## Database Schema

The initialization creates the following tables:

- `users` - User accounts and profiles
- `bookings` - Flight and package bookings
- `packages` - Travel package offerings
- `payments` - Payment transactions
- `passengers` - Booking passenger details
- `notifications` - User notifications
- `settings` - System settings

## Next Steps

After initializing the database:

1. **Start the backend**: `flask run --debug`
2. **Start the frontend**: `cd ../Thrive && npm run dev`
3. **Login**: Use any test user credentials
4. **Test**: Navigate through all dashboard features

## Notes

- All passwords are hashed using Werkzeug's security functions
- UUIDs are used for all primary keys
- Timestamps use UTC timezone
- Sample data includes realistic date ranges for testing
- Referral codes and credits are included for testing referral features

## Support

For issues or questions:
- Check the main `DASHBOARD_API_DOCUMENTATION.md`
- Review the `walkthrough.md` for complete implementation details
- Contact: support@thrivetravel.com
