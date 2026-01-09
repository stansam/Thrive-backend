from enum import Enum
from app.extensions import db


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    HELD = "held"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    REFUNDED = "refunded"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIAL = "partial"

class TripType(str, Enum):
    ONE_WAY = "one_way"
    ROUND_TRIP = "round_trip"
    MULTI_CITY = "multi_city"

class TravelClass(str, Enum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST_CLASS = "first_class"

class UserRole(str, Enum):
    CUSTOMER = "customer"
    CORPORATE = "corporate"
    ADMIN = "admin"
    AGENT = "agent"

class SubscriptionTier(str, Enum):
    NONE = "none"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"

class BookingType(str, Enum):
    FLIGHT = "flight"
    PACKAGE = "package"
    HOTEL = "hotel"
    CUSTOM = "custom"

class NotificationType(str, Enum):
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_REMINDER = "booking_reminder"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    GENERAL = "general"
