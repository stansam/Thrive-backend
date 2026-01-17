from flask import jsonify, current_app
from functools import wraps
from flask_login import current_user
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from os import getenv 
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    """Email sending utilities """
    
    @staticmethod
    def send_email(
        to: str,
        subject: str,
        body: str,
        html: str = None,
        cc: List[str] = None,
        bcc: List[str] = None
    ):
        try:
            smtp_server = os.getenv('SMTP_SERVER') if 'SMTP_SERVER' in os.environ else "smtp.gmail.com"
            smtp_port = os.getenv('SMTP_PORT') if 'SMTP_PORT' in os.environ else 587
            sender_email = os.getenv('SMTP_USERNAME')  
            sender_password = os.getenv('SMTP_PASSWORD')
            
            if html:
                message = MIMEMultipart('alternative')
                part1 = MIMEText(body, 'plain')
                part2 = MIMEText(html, 'html')
                message.attach(part1)
                message.attach(part2)
            else:
                message = MIMEText(body)
            
            message['From'] = sender_email
            message['To'] = to
            message['Subject'] = subject
            
            if cc:
                message['Cc'] = ', '.join(cc)
            
            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipients, message.as_string())
            
            current_app.logger.info(f"Email sent to {to}: {subject}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_booking_confirmation_email(booking):
        """Send booking confirmation email"""
        subject = f"Booking Confirmation - {booking.booking_reference}"
        body = f"""
        Dear {booking.customer.get_full_name()},
        
        Your booking has been confirmed!
        
        Booking Reference: {booking.booking_reference}
        From: {booking.origin}
        To: {booking.destination}
        Date: {booking.departure_date.strftime('%B %d, %Y')}
        
        Thank you for choosing Thrive Global Travel & Tours!
        """
        
        return EmailService.send_email(
            to=booking.customer.email,
            subject=subject,
            body=body
        )