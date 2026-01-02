"""
Admin API Routes
Handles all administrative functions for the Thrive platform
"""
from flask import request, current_app
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_, and_, func, desc
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.api.admin import admin_bp
from app.models import (
    User, Booking, Quote, Package, Payment, 
    ContactMessage, Notification, Passenger
)
from app.models.enums import (
    UserRole, SubscriptionTier, BookingStatus, 
    PaymentStatus, TripType
)
from app.extensions import db
from app.utils.decorators import admin_required
from app.utils.api_response import APIResponse
from app.utils.audit_logging import AuditLogger
from app.api.admin.schemas import AdminSchemas


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


# ===== USER MANAGEMENT =====

@admin_bp.route('/users', methods=['GET'])
@admin_required()
def get_users():
    """
    Get paginated list of users with filtering and search
    
    Query params:
        - page: Page number (default: 1)
        - perPage: Items per page (default: 20, max: 100)
        - search: Search in name/email
        - role: Filter by role
        - subscriptionTier: Filter by subscription
        - isActive: Filter by active status
        - sortBy: Field to sort by
        - sortOrder: asc or desc
    """
    try:
        # Get query parameters
        args = request.args.to_dict()
        pagination = AdminSchemas.validate_pagination(args)
        
        # Base query
        query = User.query
        
        # Search filter
        if 'search' in args and args['search']:
            search_term = f"%{args['search']}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        
        # Role filter
        if 'role' in args and args['role']:
            query = query.filter_by(role=UserRole(args['role']))
        
        # Subscription filter
        if 'subscriptionTier' in args and args['subscriptionTier']:
            query = query.filter_by(subscription_tier=SubscriptionTier(args['subscriptionTier']))
        
        # Active status filter
        if 'isActive' in args:
            is_active = args['isActive'].lower() == 'true'
            query = query.filter_by(is_active=is_active)
        
        # Sorting
        sort_by = args.get('sortBy', 'created_at')
        sort_order = args.get('sortOrder', 'desc')
        
        if hasattr(User, sort_by):
            order_column = getattr(User, sort_by)
            if sort_order == 'asc':
                query = query.order_by(order_column.asc())
            else:
                query = query.order_by(order_column.desc())
        else:
            query = query.order_by(desc(User.created_at))
        
        # Paginate
        paginated = query.paginate(
            page=pagination['page'],
            per_page=pagination['per_page'],
            error_out=False
        )
        
        return APIResponse.success({
            'users': [user.to_dict() for user in paginated.items],
            'pagination': {
                'page': paginated.page,
                'perPage': paginated.per_page,
                'totalPages': paginated.pages,
                'totalItems': paginated.total
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get users error: {str(e)}")
        return APIResponse.error("Failed to fetch users")


@admin_bp.route('/users/<user_id>', methods=['GET'])
@admin_required()
def get_user(user_id):
    """Get detailed user information including bookings and payments"""
    try:
        user = User.query.get(user_id)
        if not user:
            return APIResponse.not_found("User not found")
        
        # Get user's bookings
        bookings = Booking.query.filter_by(user_id=user_id).order_by(desc(Booking.created_at)).limit(10).all()
        
        # Get user's payments
        payments = Payment.query.filter_by(user_id=user_id).order_by(desc(Payment.created_at)).limit(10).all()
        
        # Get user's quotes
        quotes = Quote.query.filter_by(user_id=user_id).order_by(desc(Quote.created_at)).limit(10).all()
        
        # Calculate statistics
        total_spent = db.session.query(func.sum(Payment.amount)).filter(
            and_(Payment.user_id == user_id, Payment.status == PaymentStatus.PAID)
        ).scalar() or 0
        
        user_data = user.to_dict()
        user_data.update({
            'totalBookings': len(user.bookings.all()),
            'totalSpent': float(total_spent),
            'recentBookings': [b.to_dict() for b in bookings],
            'recentPayments': [p.to_dict() for p in payments],
            'recentQuotes': [q.to_dict() for q in quotes]
        })
        
        return APIResponse.success({'user': user_data})
        
    except Exception as e:
        current_app.logger.error(f"Get user error: {str(e)}")
        return APIResponse.error("Failed to fetch user details")


@admin_bp.route('/users/<user_id>', methods=['PATCH'])
@admin_required()
def update_user(user_id):
    """Update user details (role, subscription, status, etc.)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return APIResponse.not_found("User not found")
        
        data = request.get_json()
        is_valid, errors, cleaned_data = AdminSchemas.validate_user_update(data)
        
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Update user fields
        for key, value in cleaned_data.items():
            if key == 'role':
                setattr(user, key, UserRole(value))
            elif key == 'subscription_tier':
                setattr(user, key, SubscriptionTier(value))
            else:
                setattr(user, key, value)
        
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='user_updated',
            entity_type='user',
            entity_id=user_id,
            description=f'Admin updated user {user.email}',
            metadata=cleaned_data,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success({
            'user': user.to_dict()
        }, message='User updated successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update user error: {str(e)}")
        return APIResponse.error("Failed to update user")


@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required()
def delete_user(user_id):
    """Deactivate user account"""
    try:
        user = User.query.get(user_id)
        if not user:
            return APIResponse.not_found("User not found")
        
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='user_deactivated',
            entity_type='user',
            entity_id=user_id,
            description=f'Admin deactivated user {user.email}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success(message='User deactivated successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete user error: {str(e)}")
        return APIResponse.error("Failed to deactivate user")


@admin_bp.route('/users/stats', methods=['GET'])
@admin_required()
def get_user_stats():
    """Get user statistics"""
    try:
        # Total users
        total_users = User.query.count()
        
        # Users by role
        users_by_role = db.session.query(
            User.role, func.count(User.id)
        ).group_by(User.role).all()
        
        # Users by subscription
        users_by_subscription = db.session.query(
            User.subscription_tier, func.count(User.id)
        ).group_by(User.subscription_tier).all()
        
        # Active vs inactive
        active_users = User.query.filter_by(is_active=True).count()
        inactive_users = User.query.filter_by(is_active=False).count()
        
        # Growth trend (last 12 months)
        growth_data = []
        now = datetime.now(timezone.utc)
        for i in range(11, -1, -1):
            month_date = now - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i == 0:
                month_end = now
            else:
                next_month = month_start + timedelta(days=32)
                month_end = next_month.replace(day=1) - timedelta(seconds=1)
            
            count = User.query.filter(
                and_(
                    User.created_at >= month_start,
                    User.created_at <= month_end
                )
            ).count()
            
            growth_data.append({
                'month': month_date.strftime('%b %Y'),
                'count': count
            })
        
        return APIResponse.success({
            'totalUsers': total_users,
            'usersByRole': {role.value: count for role, count in users_by_role},
            'usersBySubscription': {tier.value: count for tier, count in users_by_subscription},
            'activeUsers': active_users,
            'inactiveUsers': inactive_users,
            'growthData': growth_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get user stats error: {str(e)}")
        return APIResponse.error("Failed to fetch user statistics")


# ===== BOOKING MANAGEMENT =====

@admin_bp.route('/bookings', methods=['GET'])
@admin_required()
def get_bookings():
    """
    Get paginated list of bookings with filtering
    
    Query params:
        - page, perPage: Pagination
        - search: Search in booking reference
        - status: Filter by status
        - bookingType: Filter by type
        - startDate, endDate: Date range filter
        - userId: Filter by user
    """
    try:
        args = request.args.to_dict()
        pagination = AdminSchemas.validate_pagination(args)
        
        query = Booking.query
        
        # Search filter
        if 'search' in args and args['search']:
            search_term = f"%{args['search']}%"
            query = query.filter(Booking.booking_reference.ilike(search_term))
        
        # Status filter
        if 'status' in args and args['status']:
            query = query.filter_by(status=BookingStatus(args['status']))
        
        # Booking type filter
        if 'bookingType' in args and args['bookingType']:
            query = query.filter_by(booking_type=args['bookingType'])
        
        # Date range filter
        start_date, end_date = AdminSchemas.validate_date_range(args)
        if start_date:
            query = query.filter(Booking.created_at >= start_date)
        if end_date:
            query = query.filter(Booking.created_at <= end_date)
        
        # User filter
        if 'userId' in args and args['userId']:
            query = query.filter_by(user_id=args['userId'])
        
        # Sort by creation date (newest first)
        query = query.order_by(desc(Booking.created_at))
        
        # Paginate
        paginated = query.paginate(
            page=pagination['page'],
            per_page=pagination['per_page'],
            error_out=False
        )
        
        # Include customer info in response
        bookings_data = []
        for booking in paginated.items:
            booking_dict = booking.to_dict()
            if booking.customer:
                booking_dict['customer'] = {
                    'id': booking.customer.id,
                    'fullName': booking.customer.get_full_name(),
                    'email': booking.customer.email
                }
            bookings_data.append(booking_dict)
        
        return APIResponse.success({
            'bookings': bookings_data,
            'pagination': {
                'page': paginated.page,
                'perPage': paginated.per_page,
                'totalPages': paginated.pages,
                'totalItems': paginated.total
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get bookings error: {str(e)}")
        return APIResponse.error("Failed to fetch bookings")


@admin_bp.route('/bookings/<booking_id>', methods=['GET'])
@admin_required()
def get_booking(booking_id):
    """Get detailed booking information"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return APIResponse.not_found("Booking not found")
        
        # Get passengers
        passengers = Passenger.query.filter_by(booking_id=booking_id).all()
        
        # Get payments
        payments = Payment.query.filter_by(booking_id=booking_id).all()
        
        booking_data = booking.to_dict()
        booking_data.update({
            'customer': booking.customer.to_dict() if booking.customer else None,
            'passengers': [p.to_dict() for p in passengers],
            'payments': [p.to_dict() for p in payments],
            'package': booking.package.to_dict() if booking.package else None,
            'agent': booking.agent.to_dict() if booking.agent else None
        })
        
        return APIResponse.success({'booking': booking_data})
        
    except Exception as e:
        current_app.logger.error(f"Get booking error: {str(e)}")
        return APIResponse.error("Failed to fetch booking details")


@admin_bp.route('/bookings/<booking_id>', methods=['PATCH'])
@admin_required()
def update_booking(booking_id):
    """Update booking details"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return APIResponse.not_found("Booking not found")
        
        data = request.get_json()
        is_valid, errors, cleaned_data = AdminSchemas.validate_booking_update(data)
        
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Update booking fields
        for key, value in cleaned_data.items():
            if key == 'status':
                setattr(booking, key, BookingStatus(value))
                if value == 'confirmed':
                    booking.confirmed_at = datetime.now(timezone.utc)
                elif value == 'cancelled':
                    booking.cancelled_at = datetime.now(timezone.utc)
            else:
                setattr(booking, key, value)
        
        booking.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='booking_updated',
            entity_type='booking',
            entity_id=booking_id,
            description=f'Admin updated booking {booking.booking_reference}',
            metadata=cleaned_data,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success({
            'booking': booking.to_dict()
        }, message='Booking updated successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update booking error: {str(e)}")
        return APIResponse.error("Failed to update booking")


@admin_bp.route('/bookings/<booking_id>/cancel', methods=['POST'])
@admin_required()
def cancel_booking(booking_id):
    """Cancel a booking with reason"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return APIResponse.not_found("Booking not found")
        
        data = request.get_json()
        is_valid, errors, cleaned_data = AdminSchemas.validate_booking_cancellation(data)
        
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now(timezone.utc)
        booking.notes = (booking.notes or '') + f"\n\nCancellation reason: {cleaned_data['reason']}"
        
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='booking_cancelled',
            entity_type='booking',
            entity_id=booking_id,
            description=f'Admin cancelled booking {booking.booking_reference}',
            metadata=cleaned_data,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success({
            'booking': booking.to_dict()
        }, message='Booking cancelled successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Cancel booking error: {str(e)}")
        return APIResponse.error("Failed to cancel booking")


@admin_bp.route('/bookings/stats', methods=['GET'])
@admin_required()
def get_booking_stats():
    """Get booking statistics"""
    try:
        # Total bookings
        total_bookings = Booking.query.count()
        
        # Bookings by status
        bookings_by_status = db.session.query(
            Booking.status, func.count(Booking.id)
        ).group_by(Booking.status).all()
        
        # Bookings by type
        bookings_by_type = db.session.query(
            Booking.booking_type, func.count(Booking.id)
        ).group_by(Booking.booking_type).all()
        
        # Total revenue
        total_revenue = db.session.query(func.sum(Booking.total_price)).scalar() or 0
        
        # Average booking value
        avg_booking_value = db.session.query(func.avg(Booking.total_price)).scalar() or 0
        
        # Monthly booking trend (last 12 months)
        booking_trend = []
        revenue_trend = []
        now = datetime.now(timezone.utc)
        
        for i in range(11, -1, -1):
            month_date = now - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i == 0:
                month_end = now
            else:
                next_month = month_start + timedelta(days=32)
                month_end = next_month.replace(day=1) - timedelta(seconds=1)
            
            count = Booking.query.filter(
                and_(
                    Booking.created_at >= month_start,
                    Booking.created_at <= month_end
                )
            ).count()
            
            revenue = db.session.query(func.sum(Booking.total_price)).filter(
                and_(
                    Booking.created_at >= month_start,
                    Booking.created_at <= month_end
                )
            ).scalar() or 0
            
            month_label = month_date.strftime('%b %Y')
            booking_trend.append({'month': month_label, 'count': count})
            revenue_trend.append({'month': month_label, 'revenue': float(revenue)})
        
        return APIResponse.success({
            'totalBookings': total_bookings,
            'bookingsByStatus': {status.value: count for status, count in bookings_by_status},
            'bookingsByType': dict(bookings_by_type),
            'totalRevenue': float(total_revenue),
            'avgBookingValue': float(avg_booking_value),
            'bookingTrend': booking_trend,
            'revenueTrend': revenue_trend
        })
        
    except Exception as e:
        current_app.logger.error(f"Get booking stats error: {str(e)}")
        return APIResponse.error("Failed to fetch booking statistics")


# ===== QUOTE MANAGEMENT =====

@admin_bp.route('/quotes', methods=['GET'])
@admin_required()
def get_quotes():
    """Get paginated list of quote requests"""
    try:
        args = request.args.to_dict()
        pagination = AdminSchemas.validate_pagination(args)
        
        query = Quote.query
        
        # Status filter
        if 'status' in args and args['search']:
            query = query.filter_by(status=args['status'])
        
        # Date range filter
        start_date, end_date = AdminSchemas.validate_date_range(args)
        if start_date:
            query = query.filter(Quote.created_at >= start_date)
        if end_date:
            query = query.filter(Quote.created_at <= end_date)
        
        # Sort by creation date
        query = query.order_by(desc(Quote.created_at))
        
        # Paginate
        paginated = query.paginate(
            page=pagination['page'],
            per_page=pagination['per_page'],
            error_out=False
        )
        
        # Include user info
        quotes_data = []
        for quote in paginated.items:
            quote_dict = quote.to_dict()
            if quote.user:
                quote_dict['user'] = {
                    'id': quote.user.id,
                    'fullName': quote.user.get_full_name(),
                    'email': quote.user.email
                }
            quotes_data.append(quote_dict)
        
        return APIResponse.success({
            'quotes': quotes_data,
            'pagination': {
                'page': paginated.page,
                'perPage': paginated.per_page,
                'totalPages': paginated.pages,
                'totalItems': paginated.total
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get quotes error: {str(e)}")
        return APIResponse.error("Failed to fetch quotes")


@admin_bp.route('/quotes/<quote_id>', methods=['GET'])
@admin_required()
def get_quote(quote_id):
    """Get detailed quote information"""
    try:
        quote = Quote.query.get(quote_id)
        if not quote:
            return APIResponse.not_found("Quote not found")
        
        quote_data = quote.to_dict()
        quote_data['user'] = quote.user.to_dict() if quote.user else None
        
        return APIResponse.success({'quote': quote_data})
        
    except Exception as e:
        current_app.logger.error(f"Get quote error: {str(e)}")
        return APIResponse.error("Failed to fetch quote details")


@admin_bp.route('/quotes/<quote_id>', methods=['PATCH'])
@admin_required()
def update_quote(quote_id):
    """Update quote (pricing, status, agent notes)"""
    try:
        quote = Quote.query.get(quote_id)
        if not quote:
            return APIResponse.not_found("Quote not found")
        
        data = request.get_json()
        is_valid, errors, cleaned_data = AdminSchemas.validate_quote_update(data)
        
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Update quote fields
        for key, value in cleaned_data.items():
            setattr(quote, key, value)
        
        # Calculate total if prices provided
        if 'quoted_price' in cleaned_data or 'service_fee' in cleaned_data:
            quoted_price = cleaned_data.get('quoted_price', quote.quoted_price or 0)
            service_fee = cleaned_data.get('service_fee', quote.service_fee or 0)
            quote.total_price = Decimal(str(quoted_price)) + Decimal(str(service_fee))
        
        if cleaned_data.get('status') == 'sent':
            quote.quoted_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='quote_updated',
            entity_type='quote',
            entity_id=quote_id,
            description=f'Admin updated quote {quote.quote_reference}',
            metadata=cleaned_data,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success({
            'quote': quote.to_dict()
        }, message='Quote updated successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update quote error: {str(e)}")
        return APIResponse.error("Failed to update quote")


@admin_bp.route('/quotes/stats', methods=['GET'])
@admin_required()
def get_quote_stats():
    """Get quote statistics"""
    try:
        total_quotes = Quote.query.count()
        
        # Quotes by status
        quotes_by_status = db.session.query(
            Quote.status, func.count(Quote.id)
        ).group_by(Quote.status).all()
        
        # Conversion rate
        converted_quotes = Quote.query.filter(Quote.converted_to_booking_id.isnot(None)).count()
        conversion_rate = (converted_quotes / total_quotes * 100) if total_quotes > 0 else 0
        
        return APIResponse.success({
            'totalQuotes': total_quotes,
            'quotesByStatus': dict(quotes_by_status),
            'convertedQuotes': converted_quotes,
            'conversionRate': round(conversion_rate, 2)
        })
        
    except Exception as e:
        current_app.logger.error(f"Get quote stats error: {str(e)}")
        return APIResponse.error("Failed to fetch quote statistics")


# ===== PACKAGE MANAGEMENT =====

@admin_bp.route('/packages', methods=['GET'])
@admin_required()
def get_packages():
    """Get paginated list of packages"""
    try:
        args = request.args.to_dict()
        pagination = AdminSchemas.validate_pagination(args)
        
        query = Package.query
        
        # Active filter
        if 'isActive' in args:
            is_active = args['isActive'].lower() == 'true'
            query = query.filter_by(is_active=is_active)
        
        # Search filter
        if 'search' in args and args['search']:
            search_term = f"%{args['search']}%"
            query = query.filter(
                or_(
                    Package.name.ilike(search_term),
                    Package.destination_city.ilike(search_term),
                    Package.destination_country.ilike(search_term)
                )
            )
        
        # Sort by creation date
        query = query.order_by(desc(Package.created_at))
        
        # Paginate
        paginated = query.paginate(
            page=pagination['page'],
            per_page=pagination['per_page'],
            error_out=False
        )
        
        return APIResponse.success({
            'packages': [pkg.to_dict() for pkg in paginated.items],
            'pagination': {
                'page': paginated.page,
                'perPage': paginated.per_page,
                'totalPages': paginated.pages,
                'totalItems': paginated.total
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get packages error: {str(e)}")
        return APIResponse.error("Failed to fetch packages")


@admin_bp.route('/packages/<package_id>', methods=['GET'])
@admin_required()
def get_package(package_id):
    """Get detailed package information"""
    try:
        package = Package.query.get(package_id)
        if not package:
            return APIResponse.not_found("Package not found")
        
        package_data = package.to_dict()
        package_data['totalBookings'] = package.bookings.count()
        
        return APIResponse.success({'package': package_data})
        
    except Exception as e:
        current_app.logger.error(f"Get package error: {str(e)}")
        return APIResponse.error("Failed to fetch package details")


@admin_bp.route('/packages', methods=['POST'])
@admin_required()
def create_package():
    """Create new travel package"""
    try:
        data = request.get_json()
        is_valid, errors, cleaned_data = AdminSchemas.validate_package_create(data)
        
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Check if slug already exists
        existing = Package.query.filter_by(slug=cleaned_data['slug']).first()
        if existing:
            cleaned_data['slug'] = f"{cleaned_data['slug']}-{datetime.now().timestamp()}"
        
        # Create package
        package = Package(**cleaned_data)
        db.session.add(package)
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='package_created',
            entity_type='package',
            entity_id=package.id,
            description=f'Admin created package {package.name}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success({
            'package': package.to_dict()
        }, message='Package created successfully', status_code=201)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create package error: {str(e)}")
        return APIResponse.error("Failed to create package")


@admin_bp.route('/packages/<package_id>', methods=['PATCH'])
@admin_required()
def update_package(package_id):
    """Update package details"""
    try:
        package = Package.query.get(package_id)
        if not package:
            return APIResponse.not_found("Package not found")
        
        data = request.get_json()
        is_valid, errors, cleaned_data = AdminSchemas.validate_package_update(data)
        
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Update package fields
        for key, value in cleaned_data.items():
            setattr(package, key, value)
        
        package.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='package_updated',
            entity_type='package',
            entity_id=package_id,
            description=f'Admin updated package {package.name}',
            metadata=cleaned_data,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success({
            'package': package.to_dict()
        }, message='Package updated successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update package error: {str(e)}")
        return APIResponse.error("Failed to update package")


@admin_bp.route('/packages/<package_id>', methods=['DELETE'])
@admin_required()
def delete_package(package_id):
    """Deactivate package"""
    try:
        package = Package.query.get(package_id)
        if not package:
            return APIResponse.not_found("Package not found")
        
        package.is_active = False
        package.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='package_deactivated',
            entity_type='package',
            entity_id=package_id,
            description=f'Admin deactivated package {package.name}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success(message='Package deactivated successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete package error: {str(e)}")
        return APIResponse.error("Failed to deactivate package")


@admin_bp.route('/packages/stats', methods=['GET'])
@admin_required()
def get_package_stats():
    """Get package statistics"""
    try:
        total_packages = Package.query.count()
        active_packages = Package.query.filter_by(is_active=True).count()
        
        # Most popular packages
        popular_packages = db.session.query(
            Package, func.count(Booking.id).label('booking_count')
        ).outerjoin(Booking).group_by(Package.id).order_by(desc('booking_count')).limit(10).all()
        
        return APIResponse.success({
            'totalPackages': total_packages,
            'activePackages': active_packages,
            'inactivePackages': total_packages - active_packages,
            'popularPackages': [{
                'package': pkg.to_dict(),
                'bookingCount': count
            } for pkg, count in popular_packages]
        })
        
    except Exception as e:
        current_app.logger.error(f"Get package stats error: {str(e)}")
        return APIResponse.error("Failed to fetch package statistics")


# ===== PAYMENT MANAGEMENT =====

@admin_bp.route('/payments', methods=['GET'])
@admin_required()
def get_payments():
    """Get paginated list of payments"""
    try:
        args = request.args.to_dict()
        pagination = AdminSchemas.validate_pagination(args)
        
        query = Payment.query
        
        # Status filter
        if 'status' in args and args['status']:
            query = query.filter_by(status=PaymentStatus(args['status']))
        
        # Date range filter
        start_date, end_date = AdminSchemas.validate_date_range(args)
        if start_date:
            query = query.filter(Payment.created_at >= start_date)
        if end_date:
            query = query.filter(Payment.created_at <= end_date)
        
        # Sort by creation date
        query = query.order_by(desc(Payment.created_at))
        
        # Paginate
        paginated = query.paginate(
            page=pagination['page'],
            per_page=pagination['per_page'],
            error_out=False
        )
        
        # Include user and booking info
        payments_data = []
        for payment in paginated.items:
            payment_dict = payment.to_dict()
            if payment.user:
                payment_dict['user'] = {
                    'id': payment.user.id,
                    'fullName': payment.user.get_full_name(),
                    'email': payment.user.email
                }
            if payment.booking:
                payment_dict['booking'] = {
                    'id': payment.booking.id,
                    'reference': payment.booking.booking_reference
                }
            payments_data.append(payment_dict)
        
        return APIResponse.success({
            'payments': payments_data,
            'pagination': {
                'page': paginated.page,
                'perPage': paginated.per_page,
                'totalPages': paginated.pages,
                'totalItems': paginated.total
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get payments error: {str(e)}")
        return APIResponse.error("Failed to fetch payments")


@admin_bp.route('/payments/<payment_id>', methods=['GET'])
@admin_required()
def get_payment(payment_id):
    """Get detailed payment information"""
    try:
        payment = Payment.query.get(payment_id)
        if not payment:
            return APIResponse.not_found("Payment not found")
        
        payment_data = payment.to_dict()
        payment_data['user'] = payment.user.to_dict() if payment.user else None
        payment_data['booking'] = payment.booking.to_dict() if payment.booking else None
        
        return APIResponse.success({'payment': payment_data})
        
    except Exception as e:
        current_app.logger.error(f"Get payment error: {str(e)}")
        return APIResponse.error("Failed to fetch payment details")


@admin_bp.route('/payments/<payment_id>/refund', methods=['POST'])
@admin_required()
def refund_payment(payment_id):
    """Process payment refund"""
    try:
        payment = Payment.query.get(payment_id)
        if not payment:
            return APIResponse.not_found("Payment not found")
        
        if payment.status != PaymentStatus.PAID:
            return APIResponse.error("Only paid payments can be refunded", status_code=400)
        
        data = request.get_json()
        is_valid, errors, cleaned_data = AdminSchemas.validate_payment_refund(data)
        
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Check refund amount doesn't exceed payment amount
        if cleaned_data['refund_amount'] > float(payment.amount):
            return APIResponse.error("Refund amount cannot exceed payment amount", status_code=400)
        
        # Update payment
        payment.refund_amount = Decimal(str(cleaned_data['refund_amount']))
        payment.refund_reason = cleaned_data['refund_reason']
        payment.refunded_at = datetime.now(timezone.utc)
        payment.status = PaymentStatus.REFUNDED
        
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='payment_refunded',
            entity_type='payment',
            entity_id=payment_id,
            description=f'Admin refunded payment {payment.payment_reference}',
            metadata=cleaned_data,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success({
            'payment': payment.to_dict()
        }, message='Payment refunded successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Refund payment error: {str(e)}")
        return APIResponse.error("Failed to process refund")


@admin_bp.route('/payments/stats', methods=['GET'])
@admin_required()
def get_payment_stats():
    """Get payment statistics"""
    try:
        total_payments = Payment.query.count()
        
        # Payments by status
        payments_by_status = db.session.query(
            Payment.status, func.count(Payment.id)
        ).group_by(Payment.status).all()
        
        # Total revenue
        total_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == PaymentStatus.PAID
        ).scalar() or 0
        
        # Total refunds
        total_refunds = db.session.query(func.sum(Payment.refund_amount)).scalar() or 0
        
        # Payments by method
        payments_by_method = db.session.query(
            Payment.payment_method, func.count(Payment.id)
        ).group_by(Payment.payment_method).all()
        
        return APIResponse.success({
            'totalPayments': total_payments,
            'paymentsByStatus': {status.value: count for status, count in payments_by_status},
            'totalRevenue': float(total_revenue),
            'totalRefunds': float(total_refunds),
            'netRevenue': float(total_revenue - total_refunds),
            'paymentsByMethod': dict(payments_by_method)
        })
        
    except Exception as e:
        current_app.logger.error(f"Get payment stats error: {str(e)}")
        return APIResponse.error("Failed to fetch payment statistics")


# ===== CONTACT MESSAGES =====

@admin_bp.route('/contacts', methods=['GET'])
@admin_required()
def get_contacts():
    """Get paginated list of contact messages"""
    try:
        args = request.args.to_dict()
        pagination = AdminSchemas.validate_pagination(args)
        
        query = ContactMessage.query
        
        # Status filter
        if 'status' in args and args['status']:
            query = query.filter_by(status=args['status'])
        
        # Priority filter
        if 'priority' in args and args['priority']:
            query = query.filter_by(priority=args['priority'])
        
        # Sort by creation date
        query = query.order_by(desc(ContactMessage.created_at))
        
        # Paginate
        paginated = query.paginate(
            page=pagination['page'],
            per_page=pagination['per_page'],
            error_out=False
        )
        
        return APIResponse.success({
            'contacts': [contact.to_dict() for contact in paginated.items],
            'pagination': {
                'page': paginated.page,
                'perPage': paginated.per_page,
                'totalPages': paginated.pages,
                'totalItems': paginated.total
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get contacts error: {str(e)}")
        return APIResponse.error("Failed to fetch contact messages")


@admin_bp.route('/contacts/<contact_id>', methods=['GET'])
@admin_required()
def get_contact(contact_id):
    """Get detailed contact message"""
    try:
        contact = ContactMessage.query.get(contact_id)
        if not contact:
            return APIResponse.not_found("Contact message not found")
        
        contact_data = contact.to_dict()
        contact_data['user'] = contact.user.to_dict() if contact.user else None
        contact_data['assignedAdmin'] = contact.assigned_admin.to_dict() if contact.assigned_admin else None
        
        return APIResponse.success({'contact': contact_data})
        
    except Exception as e:
        current_app.logger.error(f"Get contact error: {str(e)}")
        return APIResponse.error("Failed to fetch contact message")


@admin_bp.route('/contacts/<contact_id>', methods=['PATCH'])
@admin_required()
def update_contact(contact_id):
    """Update contact message (status, priority, notes)"""
    try:
        contact = ContactMessage.query.get(contact_id)
        if not contact:
            return APIResponse.not_found("Contact message not found")
        
        data = request.get_json()
        is_valid, errors, cleaned_data = AdminSchemas.validate_contact_message_update(data)
        
        if not is_valid:
            return APIResponse.validation_error(errors)
        
        # Update contact fields
        for key, value in cleaned_data.items():
            setattr(contact, key, value)
        
        if cleaned_data.get('status') == 'resolved':
            contact.resolved_at = datetime.now(timezone.utc)
        
        contact.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='contact_updated',
            entity_type='contact_message',
            entity_id=contact_id,
            description=f'Admin updated contact message from {contact.email}',
            metadata=cleaned_data,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success({
            'contact': contact.to_dict()
        }, message='Contact message updated successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update contact error: {str(e)}")
        return APIResponse.error("Failed to update contact message")


@admin_bp.route('/contacts/<contact_id>', methods=['DELETE'])
@admin_required()
def delete_contact(contact_id):
    """Delete contact message"""
    try:
        contact = ContactMessage.query.get(contact_id)
        if not contact:
            return APIResponse.not_found("Contact message not found")
        
        db.session.delete(contact)
        db.session.commit()
        
        # Log action
        admin_id = get_jwt_identity()
        AuditLogger.log_action(
            user_id=admin_id,
            action='contact_deleted',
            entity_type='contact_message',
            entity_id=contact_id,
            description=f'Admin deleted contact message from {contact.email}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return APIResponse.success(message='Contact message deleted successfully')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete contact error: {str(e)}")
        return APIResponse.error("Failed to delete contact message")
