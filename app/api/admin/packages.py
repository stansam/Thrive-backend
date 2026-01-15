from flask import request, current_app
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_, desc, func
from datetime import datetime, timezone

from app.api.admin import admin_bp
from app.models import Package, Booking
from app.extensions import db
from app.utils.decorators import admin_required
from app.utils.api_response import APIResponse
from app.utils.audit_logging import AuditLogger
from app.api.admin.schemas import AdminSchemas

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
            changes=cleaned_data,
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
