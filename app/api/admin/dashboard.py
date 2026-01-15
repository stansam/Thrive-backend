from flask import current_app
from sqlalchemy import or_, and_, func, desc
from datetime import datetime, timedelta, timezone

from app.api.admin import admin_bp
from app.models import (
    User, Booking, Quote, Package, Payment, 
    ContactMessage
)
from app.models.enums import (
    BookingStatus, PaymentStatus
)
from app.extensions import db
from app.utils.decorators import admin_required
from app.utils.api_response import APIResponse

# ===== DASHBOARD OVERVIEW =====

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required()
def get_admin_dashboard():
    """
    Get admin dashboard overview with key metrics
    
    Returns:
        - Total users (by role, new this month)
        - Total bookings (by status, revenue)
        - Pending quotes
        - Recent activity
        - System alerts
    """
    try:
        # Date ranges
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # User statistics
        total_users = User.query.count()
        new_users_month = User.query.filter(User.created_at >= month_start).count()
        users_by_role = db.session.query(
            User.role, func.count(User.id)
        ).group_by(User.role).all()
        
        # Booking statistics
        total_bookings = Booking.query.count()
        confirmed_bookings = Booking.query.filter_by(status=BookingStatus.CONFIRMED).count()
        pending_bookings = Booking.query.filter_by(status=BookingStatus.PENDING).count()
        
        # Revenue calculation
        total_revenue = db.session.query(
            func.sum(Payment.amount)
        ).filter(Payment.status == PaymentStatus.PAID).scalar() or 0
        
        month_revenue = db.session.query(
            func.sum(Payment.amount)
        ).filter(
            and_(
                Payment.status == PaymentStatus.PAID,
                Payment.created_at >= month_start
            )
        ).scalar() or 0
        
        # Quote statistics
        pending_quotes = Quote.query.filter_by(status='pending').count()
        total_quotes = Quote.query.count()
        
        # Package statistics
        active_packages = Package.query.filter_by(is_active=True).count()
        
        # Contact messages
        unread_contacts = ContactMessage.query.filter_by(status='new').count()
        
        # Recent activity - last 10 bookings
        recent_bookings = Booking.query.order_by(desc(Booking.created_at)).limit(10).all()
        
        # Recent users - last 10 registrations
        recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()
        
        # Monthly revenue trend (last 6 months)
        revenue_chart = []
        for i in range(5, -1, -1):
            month_date = now - timedelta(days=30*i)
            month_start_date = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i == 0:
                month_end_date = now
            else:
                next_month = month_start_date + timedelta(days=32)
                month_end_date = next_month.replace(day=1) - timedelta(seconds=1)
            
            month_rev = db.session.query(
                func.sum(Payment.amount)
            ).filter(
                and_(
                    Payment.status == PaymentStatus.PAID,
                    Payment.created_at >= month_start_date,
                    Payment.created_at <= month_end_date
                )
            ).scalar() or 0
            
            revenue_chart.append({
                'month': month_date.strftime('%b %Y'),
                'revenue': float(month_rev)
            })
        
        return APIResponse.success({
            'stats': {
                'totalUsers': total_users,
                'newUsersThisMonth': new_users_month,
                'usersByRole': {role.value: count for role, count in users_by_role},
                'totalBookings': total_bookings,
                'confirmedBookings': confirmed_bookings,
                'pendingBookings': pending_bookings,
                'totalRevenue': float(total_revenue),
                'monthRevenue': float(month_revenue),
                'pendingQuotes': pending_quotes,
                'totalQuotes': total_quotes,
                'activePackages': active_packages,
                'unreadContacts': unread_contacts
            },
            'recentBookings': [b.to_dict() for b in recent_bookings],
            'recentUsers': [u.to_dict() for u in recent_users],
            'revenueChart': revenue_chart
        })
        
    except Exception as e:
        current_app.logger.error(f"Admin dashboard error: {str(e)}")
        return APIResponse.error("Failed to load dashboard data")
