from flask import jsonify, current_app
from functools import wraps
from flask_login import current_user
from datetime import datetime, timedelta

class ReferralManager:
    """Handle referral system"""
    
    REFERRAL_CREDIT = Decimal('10.00')
    
    @staticmethod
    def generate_referral_code(user_id: str) -> str:
        """Generate unique referral code"""
        # Use first 4 chars of user_id + random string
        code = user_id[:4].upper() + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return code
    
    @staticmethod
    def apply_referral(referrer_id: str, referee_id: str):
        """Apply referral credit to referrer"""
        from app.models import User
        from app.extensions import db
        
        referrer = User.query.get(referrer_id)
        referee = User.query.get(referee_id)
        
        if not referrer or not referee:
            return False
        
        # Add credit to referrer
        referrer.referral_credits += ReferralManager.REFERRAL_CREDIT
        
        # Create notification
        NotificationService.create_notification(
            user_id=referrer_id,
            notification_type='referral_credit',
            title='Referral Credit Earned',
            message=f"You've earned ${ReferralManager.REFERRAL_CREDIT} credit for referring {referee.get_full_name()}!"
        )
        
        db.session.commit()
        return True
    
    @staticmethod
    def validate_referral_code(code: str) -> Optional[str]:
        """Validate referral code and return user_id"""
        from app.models import User
        
        user = User.query.filter_by(referral_code=code).first()
        return user.id if user else None