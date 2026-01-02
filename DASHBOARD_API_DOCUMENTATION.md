# Backend Dashboard API Documentation

## Overview

This document provides comprehensive documentation for the Thrive Travel dashboard client APIs. These APIs power the user dashboard, enabling users to manage their profiles, subscriptions, bookings, trips, and support requests.

**Base URL**: `/api/client/dashboard`  
**Authentication**: All endpoints require JWT authentication via Bearer token

---

## Table of Contents

1. [Authentication](#authentication)
2. [Dashboard Summary](#dashboard-summary)
3. [Profile Management](#profile-management)
4. [Subscription Management](#subscription-management)
5. [Bookings Management](#bookings-management)
6. [Trips & Tours](#trips--tours)
7. [Contact & Support](#contact--support)
8. [Notifications](#notifications)
9. [Error Handling](#error-handling)
10. [Testing](#testing)

---

## Authentication

All dashboard endpoints require a valid JWT access token obtained from the authentication endpoints.

### Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Getting an Access Token

```bash
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response includes `accessToken` to be used in subsequent requests.

---

## Dashboard Summary

### GET `/api/client/dashboard/summary`

Retrieves dashboard statistics and overview data for the authenticated user.

**Response**:
```json
{
  "success": true,
  "message": "Dashboard summary retrieved successfully",
  "data": {
    "stats": {
      "totalBookings": 15,
      "confirmedBookings": 12,
      "totalSpent": 5420.50,
      "upcomingBookings": 3,
      "activeTrips": 1,
      "unreadNotifications": 2
    },
    "recentBookings": [...],
    "chartData": [
      {"name": "Jan", "total": 1200.00},
      {"name": "Feb", "total": 1500.00},
      ...
    ],
    "subscriptionTier": "silver",
    "hasActiveSubscription": true
  }
}
```

---

## Profile Management

### GET `/api/client/dashboard/profile`

Retrieves the complete user profile.

**Response**:
```json
{
  "success": true,
  "data": {
    "profile": {
      "id": "user-uuid",
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "phone": "+1234567890",
      "dateOfBirth": "1990-01-01",
      "passportNumber": "AB123456",
      "passportExpiry": "2030-01-01",
      "nationality": "American",
      "preferredAirline": "Delta",
      "frequentFlyerNumbers": {"Delta": "123456"},
      "dietaryPreferences": "Vegetarian",
      "specialAssistance": null,
      "subscriptionTier": "silver",
      "referralCode": "JOHN123",
      "referralCredits": 25.00
    }
  }
}
```

### PUT `/api/client/dashboard/profile`

Updates user profile information.

**Request Body**:
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "phone": "+1234567890",
  "dateOfBirth": "1990-01-01",
  "passportNumber": "AB123456",
  "passportExpiry": "2030-01-01",
  "nationality": "American",
  "preferredAirline": "Delta",
  "frequentFlyerNumbers": {"Delta": "123456"},
  "dietaryPreferences": "Vegetarian",
  "specialAssistance": "Wheelchair assistance required"
}
```

**Validation Rules**:
- `firstName`, `lastName`: 2-50 characters
- `phone`: Valid international format (10-15 digits)
- `dateOfBirth`: Must be in the past, user must be 18+
- `passportExpiry`: Must be in the future
- `dietaryPreferences`: Max 200 characters
- `specialAssistance`: Max 1000 characters

**Response**:
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "data": {
    "profile": {...}
  }
}
```

---

## Subscription Management

### GET `/api/client/dashboard/subscriptions`

Retrieves subscription information and available tiers.

**Response**:
```json
{
  "success": true,
  "data": {
    "currentSubscription": {
      "tier": "silver",
      "startDate": "2024-01-01T00:00:00Z",
      "endDate": "2024-02-01T00:00:00Z",
      "isActive": true,
      "bookingsUsed": 5,
      "bookingsRemaining": 10
    },
    "availableTiers": {
      "bronze": {
        "name": "Bronze",
        "price": 29.99,
        "currency": "USD",
        "interval": "month",
        "maxBookings": 6,
        "benefits": [...]
      },
      "silver": {...},
      "gold": {...}
    }
  }
}
```

### POST `/api/client/dashboard/subscriptions/upgrade`

Upgrades user subscription with Stripe payment.

**Request Body**:
```json
{
  "tier": "silver",
  "paymentMethodId": "pm_xxxxx"
}
```

**Validation Rules**:
- `tier`: Must be one of: bronze, silver, gold
- `paymentMethodId`: Optional Stripe payment method ID

**Response**:
```json
{
  "success": true,
  "message": "Subscription upgraded successfully!",
  "data": {
    "subscription": {
      "tier": "silver",
      "startDate": "2024-01-15T10:30:00Z",
      "endDate": "2024-02-15T10:30:00Z"
    },
    "payment": {
      "id": "payment-uuid",
      "amount": 59.99,
      "status": "paid"
    }
  }
}
```

**Stripe Integration**:
- Creates Stripe customer if doesn't exist
- Processes payment via Stripe Payment Intent
- Handles 3D Secure authentication
- Sends confirmation email
- Creates notification

---

## Bookings Management

### GET `/api/client/dashboard/bookings`

Retrieves paginated list of user bookings with optional filters.

**Query Parameters**:
- `status`: Filter by status (pending, confirmed, cancelled, completed, refunded, all)
- `type`: Filter by type (flight, package, hotel, custom, all)
- `startDate`: Filter from date (YYYY-MM-DD)
- `endDate`: Filter to date (YYYY-MM-DD)
- `page`: Page number (default: 1)
- `perPage`: Items per page (default: 10, max: 100)

**Example Request**:
```
GET /api/client/dashboard/bookings?status=confirmed&type=flight&page=1&perPage=10
```

**Response**:
```json
{
  "success": true,
  "data": {
    "bookings": [
      {
        "id": "booking-uuid",
        "bookingReference": "TGT-ABC123",
        "bookingType": "flight",
        "status": "confirmed",
        "origin": "New York",
        "destination": "London",
        "departureDate": "2024-03-15T10:00:00Z",
        "returnDate": "2024-03-22T15:00:00Z",
        "totalPrice": 1200.00,
        "passengerCount": 2,
        "paymentStatus": "paid",
        "createdAt": "2024-01-10T08:30:00Z"
      },
      ...
    ],
    "pagination": {
      "page": 1,
      "perPage": 10,
      "totalPages": 3,
      "totalItems": 25,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

### GET `/api/client/dashboard/bookings/<booking_id>`

Retrieves detailed information for a specific booking.

**Response**:
```json
{
  "success": true,
  "data": {
    "booking": {
      "id": "booking-uuid",
      "bookingReference": "TGT-ABC123",
      "status": "confirmed",
      "passengers": [
        {
          "id": "passenger-uuid",
          "firstName": "John",
          "lastName": "Doe",
          "dateOfBirth": "1990-01-01",
          "passportNumber": "AB123456",
          "nationality": "American",
          "passengerType": "adult"
        }
      ],
      "payments": [
        {
          "id": "payment-uuid",
          "amount": 1200.00,
          "currency": "USD",
          "status": "paid",
          "paymentMethod": "stripe",
          "paidAt": "2024-01-10T09:00:00Z"
        }
      ],
      "package": {...}  // If booking type is package
    }
  }
}
```

### POST `/api/client/dashboard/bookings/<booking_id>/cancel`

Cancels a booking and processes refund if applicable.

**Request Body**:
```json
{
  "reason": "Change of plans",
  "requestRefund": true
}
```

**Refund Policy**:
- 24+ hours before departure: 100% refund
- 12-24 hours before departure: 50% refund
- <12 hours before departure: No refund
- Silver/Gold members: Always 100% refund

**Response**:
```json
{
  "success": true,
  "message": "Booking cancelled successfully",
  "data": {
    "booking": {
      "id": "booking-uuid",
      "bookingReference": "TGT-ABC123",
      "status": "refunded",
      "refundAmount": 1200.00
    }
  }
}
```

---

## Trips & Tours

### GET `/api/client/dashboard/trips`

Retrieves user's package tour bookings.

**Query Parameters**:
- `status`: Filter by status (active, past, all)
- `page`: Page number
- `perPage`: Items per page

**Response**:
```json
{
  "success": true,
  "data": {
    "trips": [
      {
        "id": "booking-uuid",
        "bookingReference": "TGT-PKG456",
        "status": "confirmed",
        "departureDate": "2024-04-01T00:00:00Z",
        "package": {
          "id": "package-uuid",
          "name": "Paris Adventure",
          "destination": "Paris, France",
          "duration": "7 Days / 6 Nights",
          "hotelName": "Hotel de Paris",
          "hotelRating": 5,
          "featuredImage": "https://...",
          "highlights": [...],
          "inclusions": [...],
          "itinerary": [...]
        }
      }
    ],
    "pagination": {...}
  }
}
```

### GET `/api/client/dashboard/trips/<trip_id>`

Retrieves detailed trip information including full itinerary.

---

## Contact & Support

### POST `/api/client/dashboard/contact`

Submits a support request or contact message.

**Request Body**:
```json
{
  "category": "booking",
  "subject": "Issue with booking confirmation",
  "message": "I haven't received my booking confirmation email for booking TGT-ABC123. Can you please help?",
  "bookingReference": "TGT-ABC123"
}
```

**Validation Rules**:
- `category`: Must be one of: general, booking, payment, technical, feedback
- `subject`: 5-200 characters
- `message`: 20-2000 characters
- `bookingReference`: Optional

**Response**:
```json
{
  "success": true,
  "message": "Your message has been sent successfully. We will get back to you within 24 hours."
}
```

**Actions**:
- Creates notification for admin users
- Sends confirmation email to user
- Sends notification email to support team
- Logs submission in audit log

---

## Notifications

### GET `/api/client/dashboard/notifications`

Retrieves user notifications.

**Query Parameters**:
- `page`: Page number (default: 1)
- `perPage`: Items per page (default: 20)
- `unreadOnly`: Show only unread (true/false)

**Response**:
```json
{
  "success": true,
  "data": {
    "notifications": [
      {
        "id": "notification-uuid",
        "type": "booking_confirmed",
        "title": "Booking Confirmed",
        "message": "Your booking TGT-ABC123 has been confirmed!",
        "isRead": false,
        "createdAt": "2024-01-15T10:00:00Z"
      }
    ],
    "pagination": {...}
  }
}
```

### PUT `/api/client/dashboard/notifications/<notification_id>/read`

Marks a notification as read.

**Response**:
```json
{
  "success": true,
  "message": "Notification marked as read",
  "data": {
    "notification": {
      "id": "notification-uuid",
      "isRead": true,
      "readAt": "2024-01-15T11:00:00Z"
    }
  }
}
```

---

## Error Handling

All endpoints follow a consistent error response format:

### Validation Error (422)
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "email": "Invalid email format",
    "password": "Password must be at least 8 characters"
  }
}
```

### Unauthorized (401)
```json
{
  "success": false,
  "message": "Unauthorized access"
}
```

### Not Found (404)
```json
{
  "success": false,
  "message": "Resource not found"
}
```

### Server Error (500)
```json
{
  "success": false,
  "message": "An error occurred. Please try again."
}
```

---

## Testing

### Running Tests

```bash
cd /home/vault/Documents/Bundle/backend
pytest tests/test_dashboard.py -v
```

### Test Coverage

The test suite includes:
- ✅ Dashboard summary retrieval
- ✅ Profile management (GET/PUT)
- ✅ Subscription management
- ✅ Bookings list with filters and pagination
- ✅ Booking details and cancellation
- ✅ Trips management
- ✅ Contact form submission
- ✅ Notifications management
- ✅ Validation schema edge cases
- ✅ Error scenarios
- ✅ Authentication requirements

### Example Test Run

```bash
$ pytest tests/test_dashboard.py -v

tests/test_dashboard.py::TestDashboardSummary::test_get_dashboard_summary PASSED
tests/test_dashboard.py::TestProfileManagement::test_get_profile PASSED
tests/test_dashboard.py::TestProfileManagement::test_update_profile PASSED
tests/test_dashboard.py::TestSubscriptionManagement::test_get_subscriptions PASSED
tests/test_dashboard.py::TestBookingsManagement::test_get_bookings PASSED
tests/test_dashboard.py::TestBookingsManagement::test_cancel_booking PASSED
...

====== 40 passed in 2.34s ======
```

---

## Implementation Notes

### Database Models Used

- `User`: User accounts and profiles
- `Booking`: Flight and package bookings
- `Package`: Tour packages
- `Payment`: Payment transactions
- `Notification`: User notifications
- `Passenger`: Booking passengers

### External Services

- **Stripe**: Payment processing and refunds
- **Email Service**: Transactional emails
- **Audit Logger**: Action logging
- **Notification Service**: In-app notifications

### Security Features

- JWT authentication on all endpoints
- Input validation on all requests
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention via JSON responses
- CORS configuration
- Rate limiting (recommended for production)

---

## Next Steps

1. Configure Stripe API keys (see `STRIPE_CONFIGURATION.md`)
2. Set up email service for notifications
3. Configure frontend to consume these APIs
4. Deploy to staging for testing
5. Set up monitoring and logging
6. Configure production environment variables

---

## Support

For questions or issues with these APIs:
- Review test cases in `tests/test_dashboard.py`
- Check application logs for detailed error messages
- Refer to `STRIPE_CONFIGURATION.md` for payment setup
- Contact development team

---

**Last Updated**: January 2, 2026  
**API Version**: 1.0  
**Author**: Thrive Travel Development Team
