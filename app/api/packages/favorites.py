from flask import current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.packages import packages_bp
from app.models import User
from app.utils.api_response import APIResponse

# ==================== USER FAVORITES ====================

from app.models import Package
from app.extensions import db

@packages_bp.route('/favorites', methods=['GET'])
@jwt_required()
def get_user_favorites():
    """
    Get user's favorite packages
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
             return APIResponse.error("User not found", status_code=404)

        favorites = user.favorite_packages.filter_by(is_active=True).all()
        
        return APIResponse.success(
            data=[pkg.to_dict() for pkg in favorites],
            message=f"Found {len(favorites)} favorite package(s)"
        )
            
    except Exception as e:
        current_app.logger.error(f"User favorites error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching favorites",
            status_code=500
        )

@packages_bp.route('/<package_id>/favorite', methods=['POST'])
@jwt_required()
def add_favorite(package_id):
    """Add package to favorites"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return APIResponse.error("User not found", status_code=404)
            
        package = Package.query.get(package_id)
        if not package:
            return APIResponse.error("Package not found", status_code=404)
            
        if package in user.favorite_packages:
             return APIResponse.success(message="Package already in favorites")
             
        user.favorite_packages.append(package)
        db.session.commit()
        
        return APIResponse.success(message="Package added to favorites")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add favorite error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while adding favorite",
            status_code=500
        )

@packages_bp.route('/<package_id>/favorite', methods=['DELETE'])
@jwt_required()
def remove_favorite(package_id):
    """Remove package from favorites"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return APIResponse.error("User not found", status_code=404)
            
        package = Package.query.get(package_id)
        if not package:
            return APIResponse.error("Package not found", status_code=404)
            
        if package not in user.favorite_packages:
            return APIResponse.error("Package not in favorites", status_code=400)
            
        user.favorite_packages.remove(package)
        db.session.commit()
        
        return APIResponse.success(message="Package removed from favorites")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Remove favorite error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while removing favorite",
            status_code=500
        )
