class NotificationService:
    """Handle notifications (email, SMS, in-app)"""
    
    @staticmethod
    def create_notification(
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        booking_id: str = None,
        link_url: str = None
    ):
        """Create in-app notification"""
        from app.models import Notification
        from app.extensions import db
        
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            booking_id=booking_id,
            link_url=link_url
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return notification
    
    @staticmethod
    def send_booking_confirmation(booking):
        """Send booking confirmation notification"""
        message = (
            f"Your booking {booking.booking_reference} has been confirmed! "
            f"Trip from {booking.origin} to {booking.destination} on "
            f"{booking.departure_date.strftime('%B %d, %Y')}."
        )
        
        return NotificationService.create_notification(
            user_id=booking.user_id,
            notification_type='booking_confirmed',
            title='Booking Confirmed',
            message=message,
            booking_id=booking.id,
            link_url=f'/bookings/{booking.id}'
        )
    
    @staticmethod
    def send_payment_received(payment):
        """Send payment received notification"""
        message = (
            f"Payment of ${payment.amount} received for booking "
            f"{payment.booking.booking_reference}. Thank you!"
        )
        
        return NotificationService.create_notification(
            user_id=payment.user_id,
            notification_type='payment_received',
            title='Payment Received',
            message=message,
            booking_id=payment.booking_id,
            link_url=f'/bookings/{payment.booking_id}'
        )
