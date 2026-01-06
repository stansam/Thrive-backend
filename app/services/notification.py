"""
Notification Service
Handles sending notifications to users via email, SMS, and in-app
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from flask import current_app, render_template_string
from flask_mail import Mail, Message

from app.extensions import db
from app.models.notification import Notification
from app.models.enums import NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications to users"""
    
    def __init__(self):
        self.mail = None
        
    def _create_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        booking_id: Optional[str] = None
    ) -> Notification:
        """Create a notification record in database"""
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            link_url=link_url,
            booking_id=booking_id
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not current_app.config.get('MAIL_SERVER'):
                logger.warning("Email not configured, skipping send")
                return False
            
            if not self.mail:
                self.mail = Mail(current_app)
            
            msg = Message(
                subject=subject,
                recipients=[to_email],
                html=html_body,
                body=text_body or html_body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            
            self.mail.send(msg)
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_booking_confirmation(self, user, booking) -> None:
        """
        Send booking confirmation notification
        
        Args:
            user: User model instance
            booking: Booking model instance
        """
        try:
            # Create in-app notification
            title = "Booking Confirmed!"
            message = (
                f"Your booking {booking.booking_reference} from {booking.origin} "
                f"to {booking.destination} has been confirmed."
            )
            
            notification = self._create_notification(
                user_id=user.id,
                notification_type=NotificationType.BOOKING_CONFIRMED.value,
                title=title,
                message=message,
                link_url=f"/bookings/{booking.id}",
                booking_id=booking.id
            )
            notification.sent_via_email = True
            db.session.commit()
            
            # Send email
            email_subject = f"Booking Confirmation - {booking.booking_reference}"
            email_body = self._render_booking_confirmation_email(user, booking)
            
            self._send_email(
                to_email=user.email,
                subject=email_subject,
                html_body=email_body
            )
            
            logger.info(f"Sent booking confirmation for {booking.booking_reference}")
            
        except Exception as e:
            logger.error(f"Failed to send booking confirmation: {str(e)}")
    
    def send_cancellation_notification(self, user, booking) -> None:
        """
        Send booking cancellation notification
        
        Args:
            user: User model instance
            booking: Booking model instance
        """
        try:
            # Create in-app notification
            title = "Booking Cancelled"
            message = (
                f"Your booking {booking.booking_reference} has been cancelled. "
                f"If you paid for this booking, a refund will be processed within 5-7 business days."
            )
            
            notification = self._create_notification(
                user_id=user.id,
                notification_type=NotificationType.BOOKING_CANCELLED.value,
                title=title,
                message=message,
                link_url=f"/bookings/{booking.id}",
                booking_id=booking.id
            )
            notification.sent_via_email = True
            db.session.commit()
            
            # Send email
            email_subject = f"Booking Cancelled - {booking.booking_reference}"
            email_body = self._render_cancellation_email(user, booking)
            
            self._send_email(
                to_email=user.email,
                subject=email_subject,
                html_body=email_body
            )
            
            logger.info(f"Sent cancellation notification for {booking.booking_reference}")
            
        except Exception as e:
            logger.error(f"Failed to send cancellation notification: {str(e)}")
    
    def send_payment_confirmation(self, user, payment, booking) -> None:
        """
        Send payment confirmation notification
        
        Args:
            user: User model instance
            payment: Payment model instance
            booking: Booking model instance
        """
        try:
            # Create in-app notification
            title = "Payment Received"
            message = (
                f"We have received your payment of {payment.currency} {payment.amount} "
                f"for booking {booking.booking_reference}."
            )
            
            self._create_notification(
                user_id=user.id,
                notification_type=NotificationType.PAYMENT_RECEIVED.value,
                title=title,
                message=message,
                link_url=f"/bookings/{booking.id}",
                booking_id=booking.id
            )
            
            # Send email
            email_subject = f"Payment Confirmation - {payment.payment_reference}"
            email_body = self._render_payment_confirmation_email(user, payment, booking)
            
            self._send_email(
                to_email=user.email,
                subject=email_subject,
                html_body=email_body
            )
            
            logger.info(f"Sent payment confirmation for {payment.payment_reference}")
            
        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {str(e)}")
    
    def send_booking_reminder(self, user, booking, days_until_departure: int) -> None:
        """
        Send booking reminder notification
        
        Args:
            user: User model instance
            booking: Booking model instance
            days_until_departure: Number of days until departure
        """
        try:
            # Create in-app notification
            title = "Upcoming Trip Reminder"
            message = (
                f"Your trip from {booking.origin} to {booking.destination} "
                f"is in {days_until_departure} days. Booking reference: {booking.booking_reference}"
            )
            
            self._create_notification(
                user_id=user.id,
                notification_type=NotificationType.BOOKING_REMINDER.value,
                title=title,
                message=message,
                link_url=f"/bookings/{booking.id}",
                booking_id=booking.id
            )
            
            logger.info(f"Sent booking reminder for {booking.booking_reference}")
            
        except Exception as e:
            logger.error(f"Failed to send booking reminder: {str(e)}")
    
    def _render_booking_confirmation_email(self, user, booking) -> str:
        """Render booking confirmation email HTML"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #2563eb; color: white; padding: 20px; text-align: center; }
                .content { background: #f9fafb; padding: 30px; }
                .booking-details { background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #2563eb; }
                .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }
                .button { display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Booking Confirmed!</h1>
                </div>
                <div class="content">
                    <p>Dear {{ user.first_name }},</p>
                    <p>Great news! Your flight booking has been confirmed.</p>
                    
                    <div class="booking-details">
                        <h2>Booking Details</h2>
                        <p><strong>Booking Reference:</strong> {{ booking.booking_reference }}</p>
                        <p><strong>Route:</strong> {{ booking.origin }} → {{ booking.destination }}</p>
                        <p><strong>Departure:</strong> {{ booking.departure_date.strftime('%B %d, %Y at %I:%M %p') if booking.departure_date else 'TBD' }}</p>
                        {% if booking.return_date %}
                        <p><strong>Return:</strong> {{ booking.return_date.strftime('%B %d, %Y at %I:%M %p') }}</p>
                        {% endif %}
                        <p><strong>Passengers:</strong> {{ booking.get_total_passengers() }}</p>
                        <p><strong>Total Amount:</strong> {{ booking.total_price }} USD</p>
                    </div>
                    
                    <p>Please check in online 24 hours before your flight departure.</p>
                    
                    <center>
                        <a href="{{ app_url }}/bookings/{{ booking.id }}" class="button">View Booking Details</a>
                    </center>
                    
                    <p>Have a great trip!</p>
                    <p>Best regards,<br>Thrive Tours & Travels Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Thrive Tours & Travels. All rights reserved.</p>
                    <p>This is an automated email. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(
            template,
            user=user,
            booking=booking,
            app_url=current_app.config.get('APP_URL', 'http://localhost:3000')
        )
    
    def _render_cancellation_email(self, user, booking) -> str:
        """Render booking cancellation email HTML"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #dc2626; color: white; padding: 20px; text-align: center; }
                .content { background: #f9fafb; padding: 30px; }
                .booking-details { background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #dc2626; }
                .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Booking Cancelled</h1>
                </div>
                <div class="content">
                    <p>Dear {{ user.first_name }},</p>
                    <p>Your booking has been cancelled as requested.</p>
                    
                    <div class="booking-details">
                        <h2>Cancelled Booking</h2>
                        <p><strong>Booking Reference:</strong> {{ booking.booking_reference }}</p>
                        <p><strong>Route:</strong> {{ booking.origin }} → {{ booking.destination }}</p>
                        <p><strong>Amount:</strong> {{ booking.total_price }} USD</p>
                    </div>
                    
                    <p>If you paid for this booking, a refund will be processed to your original payment method within 5-7 business days.</p>
                    
                    <p>If you have any questions, please contact our support team.</p>
                    
                    <p>Best regards,<br>Thrive Tours & Travels Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Thrive Tours & Travels. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(
            template,
            user=user,
            booking=booking
        )
    
    def _render_payment_confirmation_email(self, user, payment, booking) -> str:
        """Render payment confirmation email HTML"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #10b981; color: white; padding: 20px; text-align: center; }
                .content { background: #f9fafb; padding: 30px; }
                .payment-details { background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #10b981; }
                .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ Payment Received</h1>
                </div>
                <div class="content">
                    <p>Dear {{ user.first_name }},</p>
                    <p>We have successfully received your payment.</p>
                    
                    <div class="payment-details">
                        <h2>Payment Details</h2>
                        <p><strong>Payment Reference:</strong> {{ payment.payment_reference }}</p>
                        <p><strong>Booking Reference:</strong> {{ booking.booking_reference }}</p>
                        <p><strong>Amount:</strong> {{ payment.amount }} {{ payment.currency }}</p>
                        <p><strong>Payment Method:</strong> {{ payment.payment_method|title }}</p>
                        <p><strong>Date:</strong> {{ payment.paid_at.strftime('%B %d, %Y at %I:%M %p') if payment.paid_at else 'Processing' }}</p>
                    </div>
                    
                    <p>This receipt confirms that your payment has been processed successfully.</p>
                    
                    <p>Thank you for choosing Thrive Tours & Travels!</p>
                    
                    <p>Best regards,<br>Thrive Tours & Travels Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Thrive Tours & Travels. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(
            template,
            user=user,
            payment=payment,
            booking=booking
        )