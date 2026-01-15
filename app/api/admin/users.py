from flask import request, current_app
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_, and_, func, desc
from datetime import datetime, timedelta, timezone

from app.api.admin import admin_bp
from app.models import (
    User, Booking, Quote, Payment
)
from app.models.enums import (
    UserRole, SubscriptionTier, PaymentStatus
)
from app.extensions import db
from app.utils.decorators import admin_required
from app.utils.api_response import APIResponse
from app.utils.audit_logging import AuditLogger
from app.api.admin.schemas import AdminSchemas

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
            try:
                role = UserRole[args['role'].upper()]
                query = query.filter(User.role == role)
            except KeyError:
                return APIResponse.error("Invalid role filter")
        
        # Subscription filter
        if 'subscriptionTier' in args and args['subscriptionTier']:
            try:
                tier = SubscriptionTier[args['subscriptionTier'].upper()]
                query = query.filter(User.subscription_tier == tier)
            except KeyError:
                return APIResponse.error("Invalid subscription tier")

        # Active status filter
        if args.get('isActive') in ['true', 'false']:
            query = query.filter(
                User.is_active == (args['isActive'] == 'true')
            )
        
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
            changes=cleaned_data,
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
