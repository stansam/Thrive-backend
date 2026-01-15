from flask import request, current_app
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import desc
from datetime import datetime, timezone

from app.api.admin import admin_bp
from app.models import ContactMessage
from app.extensions import db
from app.utils.decorators import admin_required
from app.utils.api_response import APIResponse
from app.utils.audit_logging import AuditLogger
from app.api.admin.schemas import AdminSchemas

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
            changes=cleaned_data,
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
