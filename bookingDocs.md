# Flight Booking System - Complete Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup Instructions](#setup-instructions)
4. [API Documentation](#api-documentation)
5. [Frontend Integration](#frontend-integration)
6. [Payment Processing](#payment-processing)
7. [Error Handling](#error-handling)
8. [Security Considerations](#security-considerations)
9. [Testing](#testing)
10. [Deployment](#deployment)

---

## Overview

This is a production-ready flight booking system integrating:
- **Amadeus Flight API** for real-time flight search and booking
- **Stripe** for secure payment processing
- **Flask** backend with SQLAlchemy ORM
- **Next.js + TypeScript** frontend with Axios
- **Comprehensive error handling** and user feedback
- **Audit logging** and notification system

### Key Features
- ✈️ Real-time flight search (one-way, round-trip, multi-city)
- 💰 Price confirmation before booking
- 👤 Passenger information management
- 💳 Secure payment processing with Stripe
- 📧 Email notifications for bookings
- 🔄 Booking management (view, cancel, refund)
- 🔒 Role-based access control
- 📊 Audit logging for compliance

---

## Architecture

### Backend Stack
```
Flask (Python 3.9+)
├── Flask-Login (Authentication)
├── Flask-SQLAlchemy (ORM)
├── Flask-Mail (Notifications)
├── Stripe Python SDK
└── Amadeus Python SDK
```

### Frontend Stack
```
Next.js 14+ (React 18+)
├── TypeScript
├── Axios (HTTP Client)
├── Stripe.js (Payment UI)
└── Tailwind CSS (Styling)
```

### Database Schema
```
users
├── bookings (one-to-many)
│   ├── passengers (one-to-many)
│   └── payments (one-to-many)
├── notifications (one-to-many)
└── audit_logs (one-to-many)
```

---

## Setup Instructions

### 1. Backend Setup

#### Prerequisites
```bash
# Python 3.9 or higher
python --version

# PostgreSQL 13+ (or MySQL 8+)
psql --version
```

#### Environment Variables
Create a `.env` file in the backend root:

```bash
# Flask Configuration
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-in-production

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/thrive_tours

# Amadeus API
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
AMADEUS_ENV=test  # or 'production'

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email Configuration (SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@thrivetours.com

# Application
APP_URL=http://localhost:3000
FRONTEND_URL=http://localhost:3000
```

#### Install Dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Database Migration
```bash
# Initialize database
flask db init

# Create migration
flask db migrate -m "Initial migration"

# Apply migration
flask db upgrade
```

#### Run Backend Server
```bash
flask run
# Server runs on http://localhost:5000
```

---

### 2. Frontend Setup

#### Prerequisites
```bash
# Node.js 18+ and npm
node --version
npm --version
```

#### Environment Variables
Create a `.env.local` file in the frontend root:

```bash
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

#### Install Dependencies
```bash
cd frontend
npm install

# Install Stripe
npm install @stripe/stripe-js @stripe/react-stripe-js

# Install Axios
npm install axios
```

#### Run Frontend Server
```bash
npm run dev
# Server runs on http://localhost:3000
```

---

## API Documentation

### Flight Search Endpoints

#### 1. Search Flights (POST /api/flights/search)

**Request:**
```json
{
  "origin": "JFK",
  "destination": "LAX",
  "departureDate": "2025-03-15",
  "returnDate": "2025-03-20",
  "adults": 1,
  "children": 0,
  "infants": 0,
  "travelClass": "ECONOMY",
  "nonStop": false,
  "maxPrice": 1000,
  "currency": "USD",
  "maxResults": 50
}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "1",
      "source": "GDS",
      "instantTicketingRequired": false,
      "itineraries": [
        {
          "duration": "PT5H30M",
          "segments": [
            {
              "departure": {
                "iataCode": "JFK",
                "terminal": "4",
                "at": "2025-03-15T08:00:00"
              },
              "arrival": {
                "iataCode": "LAX",
                "terminal": "5",
                "at": "2025-03-15T11:30:00"
              },
              "carrierCode": "AA",
              "number": "123",
              "aircraft": {
                "code": "738"
              },
              "duration": "PT5H30M"
            }
          ]
        }
      ],
      "price": {
        "currency": "USD",
        "total": "450.00",
        "base": "350.00",
        "fees": [
          {
            "amount": "100.00",
            "type": "TICKETING"
          }
        ]
      },
      "travelerPricings": [
        {
          "travelerId": "1",
          "fareOption": "STANDARD",
          "travelerType": "ADULT",
          "price": {
            "currency": "USD",
            "total": "450.00",
            "base": "350.00"
          }
        }
      ]
    }
  ],
  "meta": {
    "count": 10
  },
  "dictionaries": {
    "carriers": {
      "AA": "American Airlines"
    },
    "aircraft": {
      "738": "Boeing 737-800"
    }
  }
}
```

**Response (Error - 400):**
```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "Invalid departure date",
  "details": {
    "field": "departureDate",
    "value": "2025-13-45"
  }
}
```

#### 2. Multi-City Search (POST /api/flights/search/multi-city)

**Request:**
```json
{
  "segments": [
    {
      "origin": "MAD",
      "destination": "PAR",
      "departureDate": "2025-03-15"
    },
    {
      "origin": "PAR",
      "destination": "MUC",
      "departureDate": "2025-03-20"
    }
  ],
  "adults": 1,
  "travelClass": "ECONOMY",
  "maxResults": 20
}
```

#### 3. Confirm Price (POST /api/flights/price)

**Request:**
```json
{
  "flightOffers": [...],  // Flight offer from search results
  "include": ["credit-card-fees", "bags"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "flightOffers": [
      {
        "id": "1",
        "price": {
          "currency": "USD",
          "total": "455.00",
          "base": "350.00"
        }
      }
    ]
  },
  "warnings": [
    {
      "status": 200,
      "code": 1,
      "title": "Price increased",
      "detail": "Price has increased by 5.00 USD"
    }
  ]
}
```

---

### Booking Endpoints

#### 4. Create Booking (POST /api/flights/book)

**Request:**
```json
{
  "flightOffers": [...],  // Confirmed flight offer
  "travelers": [
    {
      "firstName": "JOHN",
      "lastName": "DOE",
      "dateOfBirth": "1990-01-01",
      "gender": "MALE",
      "email": "[email protected]",
      "phone": {
        "countryCode": "1",
        "number": "5551234567"
      },
      "documents": [
        {
          "documentType": "PASSPORT",
          "number": "A12345678",
          "expiryDate": "2028-12-31",
          "issuanceCountry": "US",
          "nationality": "US"
        }
      ],
      "travelerType": "ADULT"
    }
  ],
  "paymentMethod": "card",
  "specialRequests": "Window seat preferred"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Booking created successfully",
  "data": {
    "bookingId": "550e8400-e29b-41d4-a716-446655440000",
    "bookingReference": "TGT-ABC123",
    "paymentId": "660e8400-e29b-41d4-a716-446655440000",
    "amount": 455.00,
    "currency": "USD",
    "status": "pending"
  }
}
```

#### 5. Confirm Booking (POST /api/flights/book/confirm)

**Request:**
```json
{
  "bookingId": "550e8400-e29b-41d4-a716-446655440000",
  "paymentIntentId": "pi_3NUfDY2eZvKYlo2C0NWcvfpo"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Booking confirmed successfully",
  "data": {
    "bookingReference": "TGT-ABC123",
    "status": "confirmed",
    "confirmationNumber": "AA123456"
  }
}
```

#### 6. Get User Bookings (GET /api/flights/bookings)

**Query Parameters:**
- `page` (optional, default: 1)
- `per_page` (optional, default: 20)
- `status` (optional: pending, confirmed, cancelled)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "bookingReference": "TGT-ABC123",
      "status": "confirmed",
      "origin": "JFK",
      "destination": "LAX",
      "departureDate": "2025-03-15T08:00:00Z",
      "returnDate": "2025-03-20T15:00:00Z",
      "totalPrice": 455.00,
      "passengers": 1,
      "createdAt": "2025-01-05T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "perPage": 20,
    "total": 5,
    "pages": 1
  }
}
```

#### 7. Get Booking Details (GET /api/flights/bookings/{booking_id})

#### 8. Cancel Booking (POST /api/flights/bookings/{booking_id}/cancel)

---

### Payment Endpoints

#### 9. Create Payment Intent (POST /api/payments/create-intent)

**Request:**
```json
{
  "bookingId": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 455.00,
  "currency": "USD"
}
```

**Response:**
```json
{
  "success": true,
  "clientSecret": "pi_3NUfDY2eZvKYlo2C0NWcvfpo_secret_xyz",
  "paymentIntentId": "pi_3NUfDY2eZvKYlo2C0NWcvfpo"
}
```

#### 10. Confirm Payment (POST /api/payments/confirm)

#### 11. Process Refund (POST /api/payments/refund)

**Request:**
```json
{
  "paymentId": "660e8400-e29b-41d4-a716-446655440000",
  "amount": 455.00,  // Optional, full refund if not provided
  "reason": "Customer requested cancellation"
}
```

---

## Frontend Integration

### Basic Flight Search Example

```typescript
// pages/flights/search.tsx
import { useState } from 'react';
import { flightApi, FlightSearchParams } from '@/lib/api/flightApi';
import { AdvancedFlightSearch } from '@/components/advanced-flight-search';

export default function FlightSearchPage() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (params: FlightSearchParams) => {
    setLoading(true);
    setError(null);

    try {
      const response = await flightApi.searchFlights(params);
      
      if (response.success && response.data) {
        setResults(response.data);
      } else {
        setError(response.message || 'Search failed');
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <AdvancedFlightSearch onSearch={handleSearch} />
      
      {loading && <div>Searching flights...</div>}
      
      {error && (
        <div className="bg-red-100 text-red-700 p-4 rounded">
          {error}
        </div>
      )}
      
      {results.length > 0 && (
        <div>
          {/* Render flight results */}
        </div>
      )}
    </div>
  );
}
```

### Payment Integration Example

```typescript
// components/payment-form.tsx
import { useState } from 'react';
import {
  useStripe,
  useElements,
  PaymentElement
} from '@stripe/react-stripe-js';
import { paymentApi } from '@/lib/api/paymentApi';

interface PaymentFormProps {
  bookingId: string;
  amount: number;
  currency: string;
}

export function PaymentForm({ bookingId, amount, currency }: PaymentFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      const result = await paymentApi.processPaymentWithElements(
        elements,
        bookingId,
        amount,
        currency
      );

      if (result.success) {
        // Payment successful - redirect to confirmation
        window.location.href = `/bookings/${bookingId}/confirmation`;
      } else {
        setError(result.message);
      }
    } catch (err: any) {
      setError(err.message || 'Payment failed');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <PaymentElement />
      
      {error && (
        <div className="text-red-600 mt-2">{error}</div>
      )}
      
      <button
        type="submit"
        disabled={!stripe || processing}
        className="mt-4 w-full bg-blue-600 text-white py-2 rounded"
      >
        {processing ? 'Processing...' : `Pay ${currency} ${amount}`}
      </button>
    </form>
  );
}
```

### Complete Booking Flow

```typescript
// pages/bookings/create.tsx
import { useState } from 'react';
import { Elements } from '@stripe/react-stripe-js';
import { paymentApi } from '@/lib/api/paymentApi';
import { flightApi } from '@/lib/api/flightApi';
import { TravelerDetailsForm } from '@/components/traveler-details-form';
import { PaymentForm } from '@/components/payment-form';

export default function CreateBookingPage() {
  const [step, setStep] = useState(1);
  const [bookingData, setBookingData] = useState(null);
  const [clientSecret, setClientSecret] = useState('');
  const [stripePromise, setStripePromise] = useState(null);

  // Step 1: Confirm price
  const handlePriceConfirmation = async (flightOffer) => {
    try {
      const response = await flightApi.confirmPrice([flightOffer]);
      if (response.success) {
        setStep(2);
      }
    } catch (error) {
      console.error('Price confirmation failed:', error);
    }
  };

  // Step 2: Submit traveler details and create booking
  const handleTravelerSubmit = async (travelers) => {
    try {
      const response = await flightApi.createBooking({
        flightOffers: [confirmedOffer],
        travelers,
        paymentMethod: 'card'
      });

      if (response.success) {
        // Create payment intent
        const intentResponse = await paymentApi.createPaymentIntent({
          bookingId: response.data.bookingId,
          amount: response.data.amount,
          currency: response.data.currency
        });

        if (intentResponse.success) {
          setClientSecret(intentResponse.data.clientSecret);
          setBookingData(response.data);
          
          // Initialize Stripe
          const stripe = await paymentApi.getStripe();
          setStripePromise(stripe);
          
          setStep(3);
        }
      }
    } catch (error) {
      console.error('Booking creation failed:', error);
    }
  };

  return (
    <div>
      {step === 1 && <div>Price Confirmation</div>}
      
      {step === 2 && (
        <TravelerDetailsForm onSubmit={handleTravelerSubmit} />
      )}
      
      {step === 3 && clientSecret && stripePromise && (
        <Elements stripe={stripePromise} options={{ clientSecret }}>
          <PaymentForm
            bookingId={bookingData.bookingId}
            amount={bookingData.amount}
            currency={bookingData.currency}
          />
        </Elements>
      )}
    </div>
  );
}
```

---

## Error Handling

### Backend Error Responses

All API endpoints return consistent error formats:

```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    // Additional error context
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `MISSING_FIELDS` | 400 | Required fields missing |
| `BOOKING_NOT_FOUND` | 404 | Booking doesn't exist |
| `PAYMENT_FAILED` | 400 | Payment processing failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `API_ERROR` | 500 | External API error |
| `INTERNAL_ERROR` | 500 | Server error |

### Frontend Error Handling

```typescript
try {
  const response = await flightApi.searchFlights(params);
  // Handle success
} catch (error) {
  if (error instanceof FlightApiError) {
    // Handle specific error types
    if (error.errorCode === 'RATE_LIMIT_EXCEEDED') {
      toast.error('Too many requests. Please wait a moment.');
    } else if (error.errorCode === 'VALIDATION_ERROR') {
      toast.error(`Invalid input: ${error.message}`);
    } else {
      toast.error(error.message);
    }
  } else {
    toast.error('An unexpected error occurred');
  }
}
```

---

## Security Considerations

### 1. Authentication
- Use Flask-Login for session management
- Implement JWT tokens for API authentication
- Set secure, httpOnly cookies

### 2. API Keys
- **Never** expose Amadeus or Stripe keys in frontend
- Use environment variables
- Rotate keys regularly

### 3. Payment Security
- PCI compliance through Stripe
- Never store card numbers
- Use Stripe's secure payment elements

### 4. Data Validation
- Validate all inputs on backend
- Sanitize user data
- Use parameterized queries

### 5. Rate Limiting
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@bp.route('/search', methods=['POST'])
@limiter.limit("10 per minute")
def search_flights():
    # ...
```

---

## Testing

### Backend Tests

```python
# tests/test_flights.py
import pytest
from app import create_app
from app.extensions import db

@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_flight_search(client):
    response = client.post('/api/flights/search', json={
        'origin': 'JFK',
        'destination': 'LAX',
        'departureDate': '2025-03-15',
        'adults': 1
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert 'data' in data
```

### Frontend Tests

```typescript
// __tests__/flightApi.test.ts
import { flightApi } from '@/lib/api/flightApi';

describe('Flight API', () => {
  it('should search flights successfully', async () => {
    const params = {
      origin: 'JFK',
      destination: 'LAX',
      departureDate: '2025-03-15',
      adults: 1
    };
    
    const response = await flightApi.searchFlights(params);
    
    expect(response.success).toBe(true);
    expect(response.data).toBeDefined();
  });
});
```

---

## Deployment

### Backend Deployment (Heroku Example)

```bash
# Install Heroku CLI
heroku login

# Create app
heroku create thrive-tours-api

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-production-key
heroku config:set AMADEUS_CLIENT_ID=your-id
heroku config:set AMADEUS_CLIENT_SECRET=your-secret
heroku config:set STRIPE_SECRET_KEY=sk_live_...

# Deploy
git push heroku main

# Run migrations
heroku run flask db upgrade
```

### Frontend Deployment (Vercel)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard:
# - NEXT_PUBLIC_API_URL
# - NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
```

---

## Support & Troubleshooting

### Common Issues

**1. Amadeus API errors:**
- Verify credentials are correct
- Check API limits (test: 40 calls/sec, prod: varies)
- Ensure dates are in correct format (YYYY-MM-DD)

**2. Payment failures:**
- Test with Stripe test cards: 4242 4242 4242 4242
- Verify webhook endpoint is configured
- Check Stripe dashboard for error logs

**3. CORS errors:**
```python
from flask_cors import CORS
CORS(app, origins=['http://localhost:3000'])
```

---

## License

MIT License - See LICENSE file for details

## Contributors

- Development Team at Thrive Tours & Travels

For questions or support, contact: [email protected]