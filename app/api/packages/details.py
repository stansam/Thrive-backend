from flask import request, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from sqlalchemy import or_, and_, desc

from app.api.packages import packages_bp
from app.models import Package, User
from app.extensions import db
from app.utils.api_response import APIResponse
from app.utils.audit_logging import AuditLogger

# ==================== PACKAGE DETAIL ENDPOINTS ====================

@packages_bp.route('/<package_id>', methods=['GET'])
def get_package_detail(package_id):
    """
    Get detailed information about a specific package
    Path Parameters:
        package_id: Package UUID
    """
    try:
        package = Package.query.get(package_id)
        
        if not package:
            return APIResponse.not_found("Package not found")
        
        if not package.is_active:
            return APIResponse.error(
                "This package is currently unavailable",
                status_code=410
            )
        
        # Increment view count
        package.view_count += 1
        db.session.commit()

        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity() 
            current_user = User.query.get(current_user_id)
        except Exception:
            current_user = None
        
        if current_user:
            try:
                AuditLogger.log_action(
                    user_id=current_user.id,
                    action='VIEW_PACKAGE',
                    entity_type='Package',
                    entity_id=package_id,
                    description=f"Viewed package: {package.name}",
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            except Exception as log_error:
                current_app.logger.warning(f"Audit log error: {str(log_error)}")
        
        return APIResponse.success(
            data=package.to_dict(),
            message="Package details retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Package detail error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching package details",
            status_code=500
        )


@packages_bp.route('/slug/<slug>', methods=['GET'])
def get_package_by_slug(slug):
    """
    Get package by URL-friendly slug
    Path Parameters:
        slug: Package slug
    """
    try:
        package = Package.query.filter_by(slug=slug).first()
        
        if not package:
            return APIResponse.not_found("Package not found")
        
        if not package.is_active:
            return APIResponse.error(
                "This package is currently unavailable",
                status_code=410
            )
        
        # Increment view count
        package.view_count += 1
        db.session.commit()
        
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity() 
            current_user = User.query.get(current_user_id)
        except Exception:
            current_user = None
        
        # Log view action if user is authenticated
        if current_user:
            try:
                AuditLogger.log_action(
                    user_id=current_user.id,
                    action='VIEW_PACKAGE',
                    entity_type='Package',
                    entity_id=package.id,
                    description=f"Viewed package: {package.name}",
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            except Exception as log_error:
                current_app.logger.warning(f"Audit log error: {str(log_error)}")
        
        return APIResponse.success(
            data=package.to_dict(),
            message="Package details retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Package slug error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching package details",
            status_code=500
        )


@packages_bp.route('/similar/<package_id>', methods=['GET'])
def get_similar_packages(package_id):
    """
    Get similar packages based on destination and price range
    """
    try:
        package = Package.query.get(package_id)
        
        if not package:
            return APIResponse.not_found("Package not found")
        
        limit = min(request.args.get('limit', 5, type=int), 20)
        
        # Calculate price range (±30%)
        price_margin = float(package.starting_price) * 0.3
        min_price = float(package.starting_price) - price_margin
        max_price = float(package.starting_price) + price_margin
        
        # Find similar packages
        similar_packages = Package.query.filter(
            Package.id != package_id,
            Package.is_active == True,
            or_(
                # Same destination
                and_(
                    Package.destination_city == package.destination_city,
                    Package.destination_country == package.destination_country
                ),
                # Similar price range
                and_(
                    Package.starting_price >= min_price,
                    Package.starting_price <= max_price
                )
            )
        ).order_by(
            # Prioritize same destination
            desc(
                and_(
                    Package.destination_city == package.destination_city,
                    Package.destination_country == package.destination_country
                )
            ),
            desc(Package.is_featured),
            desc(Package.booking_count)
        ).limit(limit).all()
        
        return APIResponse.success(
            data=[pkg.to_dict() for pkg in similar_packages],
            message=f"Found {len(similar_packages)} similar package(s)"
        )
        
    except Exception as e:
        current_app.logger.error(f"Similar packages error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching similar packages",
            status_code=500
        )
