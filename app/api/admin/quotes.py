from flask import request, current_app
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import desc, func
from datetime import datetime, timezone
from decimal import Decimal

from app.api.admin import admin_bp
from app.models import Quote, Booking
from app.extensions import db
from app.utils.decorators import admin_required
from app.utils.api_response import APIResponse
from app.utils.audit_logging import AuditLogger
from app.api.admin.schemas import AdminSchemas

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
            changes=cleaned_data,
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
