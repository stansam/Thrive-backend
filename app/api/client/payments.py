
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_, desc

from app.models import User, Payment, Booking
from app.models.enums import PaymentStatus
from app.utils.api_response import APIResponse

from . import client_bp

@client_bp.route('/payments', methods=['GET'])
@jwt_required()
def get_payments():
    """
    Get user payment history
    
    Query Parameters:
        page: Page number (default: 1)
        perPage: Items per page (default: 10)
        status: Filter by status (paid, pending, failed, refunded)
        fromDate: Filter by date (YYYY-MM-DD)
        toDate: Filter by date (YYYY-MM-DD)
        
    Returns:
        200: List of payments with pagination
        401: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return APIResponse.unauthorized('User not found or inactive')
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('perPage', 10))
        status = request.args.get('status')
        from_date = request.args.get('fromDate')
        to_date = request.args.get('toDate')
        
        # Build query
        query = Payment.query.filter_by(user_id=current_user_id)
        
        # Apply filters
        if status and status != 'all':
            try:
                # Map string status to enum if needed, or rely on exact match if frontend sends correct values
                status_enum = PaymentStatus(status)
                query = query.filter(Payment.status == status_enum)
            except ValueError:
                pass # Ignore invalid status filter
                
        if from_date:
            query = query.filter(Payment.created_at >= from_date)
            
        if to_date:
            # Add one day to to_date to include the entire day
            query = query.filter(Payment.created_at <= to_date + ' 23:59:59')
            
        # Order by newest first
        query = query.order_by(desc(Payment.created_at))
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format response
        payments_data = []
        for payment in pagination.items:
            payment_dict = payment.to_dict()
            
            # Enrich with booking info if available
            if payment.booking:
                payment_dict['description'] = f"Booking {payment.booking.booking_reference}"
                payment_dict['booking_reference'] = payment.booking.booking_reference
                payment_dict['booking_type'] = payment.booking.booking_type
            else:
                # Check metadata for subscription info
                meta = payment.payment_metadata or {}
                if meta.get('type') == 'subscription':
                    tier = meta.get('subscription_tier', '')
                    payment_dict['description'] = f"{tier.title()} Subscription Upgrade" if tier else "Subscription Payment"
                    payment_dict['booking_type'] = 'subscription'
                else:
                    payment_dict['description'] = "Payment"
                    
            payments_data.append(payment_dict)
            
        return APIResponse.success(
            data={
                'payments': payments_data,
                'pagination': {
                    'page': pagination.page,
                    'perPage': pagination.per_page,
                    'totalPages': pagination.pages,
                    'totalItems': pagination.total
                }
            },
            message='Payment history retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Get payments error: {str(e)}")
        return APIResponse.error('An error occurred while fetching payment history')
