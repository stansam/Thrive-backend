from flask import jsonify, current_app
from functools import wraps
from flask_login import current_user
from datetime import datetime, timedelta, timezone
from decimal import Decimal

class SubscriptionManager:
    """Handle subscription management"""
    
    SUBSCRIPTION_PRICES = {
        'bronze': Decimal('150.00'),
        'silver': Decimal('300.00'),
        'gold': Decimal('500.00')
    }
    
    BOOKING_LIMITS = {
        'bronze': 6,
        'silver': 15,
        'gold': None  # Unlimited
    }
    
    @staticmethod
    def activate_subscription(user, tier: str, duration_months: int = 1):
        """Activate or upgrade subscription"""
        from app.extensions import db
        
        user.subscription_tier = tier
        user.subscription_start = datetime.now(timezone.utc)
        user.subscription_end = datetime.now(timezone.utc) + timedelta(days=30 * duration_months)
        user.monthly_bookings_used = 0
        
        db.session.commit()
        return user
    
    @staticmethod
    def check_booking_limit(user) -> Tuple[bool, str]:
        """Check if user can make more bookings"""
        if user.subscription_tier.value == 'gold':
            return True, "Unlimited bookings"
        
        limit = SubscriptionManager.BOOKING_LIMITS.get(
            user.subscription_tier.value,
            None
        )
        
        if limit is None:
            return True, "No subscription"
        
        if user.monthly_bookings_used >= limit:
            return False, f"Monthly limit of {limit} bookings reached"
        
        return True, f"{limit - user.monthly_bookings_used} bookings remaining"
    
    @staticmethod
    def reset_monthly_counters():
        """Reset monthly booking counters (run as scheduled task)"""
        from app.models import User
        from app.extensions import db
        
        User.query.filter(
            User.subscription_tier.in_(['bronze', 'silver', 'gold'])
        ).update({'monthly_bookings_used': 0})
        
        db.session.commit()