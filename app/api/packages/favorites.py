from flask import current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.packages import packages_bp
from app.models import User
from app.utils.api_response import APIResponse

# ==================== USER FAVORITES ====================

@packages_bp.route('/favorites', methods=['GET'])
@jwt_required()
def get_user_favorites():
    """
    Get user's favorite packages (requires favorites relationship in User model)
    """
    try:
        # This assumes a many-to-many relationship between User and Package
        # You'll need to implement this in your models
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if hasattr(user, 'favorite_packages'):
            favorites = user.favorite_packages.filter_by(is_active=True).all()
            return APIResponse.success(
                data=[pkg.to_dict() for pkg in favorites],
                message=f"Found {len(favorites)} favorite package(s)"
            )
        else:
            return APIResponse.error(
                "Favorites feature not implemented",
                status_code=501
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
    return APIResponse.error("Favorites feature not implemented", status_code=501)

@packages_bp.route('/<package_id>/favorite', methods=['DELETE'])
@jwt_required()
def remove_favorite(package_id):
    """Remove package from favorites"""
    return APIResponse.error("Favorites feature not implemented", status_code=501)
