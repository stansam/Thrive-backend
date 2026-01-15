from flask import request, current_app
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, desc
from datetime import datetime, timezone
from decimal import Decimal

from app.api.admin import admin_bp
from app.models import Payment
from app.models.enums import PaymentStatus
from app.extensions import db
from app.utils.decorators import admin_required
from app.utils.api_response import APIResponse
from app.utils.audit_logging import AuditLogger
from app.api.admin.schemas import AdminSchemas

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
            changes=cleaned_data,
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
